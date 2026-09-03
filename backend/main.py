# main.py —— 「智愿」后端入口（FastAPI）
# step11：实现 /api/data（先 mock）+ /api/health + 静态托管前端
# step13：/api/data 改走 plan_service（LLM 接入，无 Key 时 fallback 到 mock）
# step15：挂载注册/登录路由
# step16：日志（控制台实时输出 + 按天切割/定时写盘）

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# 确保能找到同级模块（uvicorn 启动时 cwd 在 backend/，通常 OK）
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402  先加载 config，顺便把 .env 读入
from schemas import PlanRequest, PlanResponse  # noqa: E402
from services.plan_service import generate_plan  # noqa: E402

WORKSPACE = Path(__file__).resolve().parent.parent

# ===================================================================
# 第16步：日志系统（实时控制台 + 定时写盘，每天一份日志文件）
# ===================================================================
LOG_DIR = config.app.LOG_DIR
LOG_DIR.mkdir(exist_ok=True)
LOG_FMT = "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"

_root = logging.getLogger()
_root.setLevel(logging.INFO)
# 避免重复添加 handler（uvicorn reload 会多次 import）
if not _root.handlers:
    _ch = logging.StreamHandler()
    _ch.setFormatter(logging.Formatter(LOG_FMT))
    _root.addHandler(_ch)

    _fh = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / "app.log",
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    _fh.setFormatter(logging.Formatter(LOG_FMT))
    _fh.suffix = "%Y-%m-%d"
    _root.addHandler(_fh)

log = logging.getLogger("app")


# ===================================================================
# FastAPI 初始化
# ===================================================================
app = FastAPI(title="智愿后端", version="0.2.0")

# CORS：本地开发放开；生产第17步改成作品集+部署域名白名单
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    t0 = datetime.now()
    log.info("> %s %s", request.method, request.url.path)
    try:
        resp = await call_next(request)
    except Exception as e:
        dt = (datetime.now() - t0).total_seconds() * 1000
        log.error("< %s %s | 500 | %.1fms | %s", request.method, request.url.path, dt, e)
        raise
    dt = (datetime.now() - t0).total_seconds() * 1000
    log.info("< %s %s | %d | %.1fms", request.method, request.url.path, resp.status_code, dt)
    return resp


@app.on_event("startup")
def on_startup():
    log.info("==== 智愿后端启动 ====")
    log.info("Workdir: %s", WORKSPACE)
    log.info("LLM: enabled=%s  model=%s  base=%s",
             config.llm.ENABLED, config.llm.MODEL, config.llm.BASE_URL)
    log.info("Logs dir: %s", LOG_DIR)
    # 预加载专业目录知识库（L1 咨询顾问用）
    try:
        from data.major_catalog import get_catalog
        cat = get_catalog()
        log.info("Major catalog loaded: %d majors.", len(cat.items))
    except Exception as e:
        log.warning("Major catalog load failed (可以忽略): %s", e)


# ===================================================================
# 接口
# ===================================================================
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "zhiyuan-backend", "llm": config.llm.ENABLED,
            "version": app.version}


@app.post("/api/data", response_model=PlanResponse)
async def gen_plan(req: PlanRequest):
    """
    step13：接 LLM 生成方案；未配置 Key 时 fallback 到 mock。
    返回结构严格与前端 planData / test_data.js 一致：
      {autoModeTag, score, s06, s07, s08, s09}
    """
    log.info("gen_plan: province=%s score=%s subjects=%s strategy=%s",
             req.province, req.score, req.subjects, req.strategy)
    plan = await generate_plan(req)
    return JSONResponse(plan)


# ===================================================================
# 第15步：注册/登录路由（按需挂载，不配置 MySQL 时可跳过）
# ===================================================================
try:
    from routers.auth import router as auth_router  # noqa: F401

    app.include_router(auth_router, prefix="/api")
    log.info("登录系统（/api/register, /api/login）已挂载")
except Exception as e:
    log.info("登录系统未挂载（MySQL 或依赖缺失可忽略）：%s", e)


# ===================================================================
# 新增：专业顾问问答路由（/api/consult/*）
# ===================================================================
try:
    from routers.consult import router as consult_router  # noqa: F401

    app.include_router(consult_router, prefix="/api")
    log.info("专业顾问系统（/api/consult/chat, /api/consult/majors）已挂载")
except Exception as e:
    log.warning("专业顾问路由挂载失败（不影响其它功能，检查下模块 import）：%s", e)


# ===================================================================
# 前端静态资源（白名单，避免暴露源码）
# ===================================================================
_ALLOWED_STATIC = {
    "zhiyuan_app.html", "data.js", "test_data.js",
    "高考志愿线框图.html", "需求调研.md", "高考志愿PRD.md", "后端架构设计.md",
}


def _static(name: str) -> FileResponse | JSONResponse:
    if name not in _ALLOWED_STATIC:
        return JSONResponse({"error": "not found"}, status_code=404)
    p = WORKSPACE / name
    if not p.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    if name.endswith(".js"):
        return FileResponse(p, media_type="text/javascript")
    if name.endswith(".md"):
        return FileResponse(p, media_type="text/markdown; charset=utf-8")
    return FileResponse(p)


@app.get("/")
def index():
    return _static("zhiyuan_app.html")


@app.get("/{path:path}")
def other_static(path: str):
    return _static(path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
