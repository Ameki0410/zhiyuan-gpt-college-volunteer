# routers/consult.py —— 专业顾问问答路由
# 接口清单（基线）：
#   POST /api/consult/chat     一次提问-回答（带 history）
#   GET  /api/consult/majors   专业目录搜索（前端联想 / 搜索参考）
# 限流：同一 IP 游客 10 次/分、登录用户 30 次/分（简易版：内存 + time 窗口）

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.consult_service import ConsultReply, consult
from data.major_catalog import get_catalog

log = logging.getLogger(__name__)
router = APIRouter(prefix="/consult", tags=["专业顾问问答"])


# ---------- Pydantic ----------
class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    source: str                    # llm / mock / refuse
    hits: list[str] = []           # 命中的参考专业名
    latency_ms: int = 0


class MajorItemOut(BaseModel):
    code: str
    name: str
    cat: str
    cat2: str
    degree: str
    years: str
    tags: list[str]
    note: str = ""


# ---------- 限流：简易内存滑窗 ----------
# 生产环境可替换成 Redis ZSET；本项目本地/小流量足够
class _RateLimit:
    def __init__(self, per_minute_default: int = 10):
        self.per_minute_default = per_minute_default
        # {key: [ts1, ts2, ...]}  只存最近 60s
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._last_clean: float = time.time()

    def _clean(self, now: float):
        if now - self._last_clean < 20:
            return
        self._last_clean = now
        cutoff = now - 60
        for k in list(self._buckets.keys()):
            new_list = [t for t in self._buckets[k] if t >= cutoff]
            if new_list:
                self._buckets[k] = new_list
            else:
                del self._buckets[k]

    def check(self, key: str, limit: int | None = None) -> bool:
        """True = 允许；False = 超限。"""
        now = time.time()
        self._clean(now)
        cutoff = now - 60
        lst = [t for t in self._buckets[key] if t >= cutoff]
        if len(lst) >= (limit or self.per_minute_default):
            return False
        lst.append(now)
        self._buckets[key] = lst
        return True


_rl_ip = _RateLimit(per_minute_default=10)  # 游客 10 次/分


def _ip_key(request: Request) -> str:
    # 如有反代（X-Forwarded-For），拆第一个
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        ip = xff.split(",", 1)[0].strip()
    else:
        ip = getattr(request.client, "host", "unknown") or "unknown"
    return ip


# ---------- 接口 ----------
@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, request: Request):
    # 1) 限流（游客：IP 10/分钟；如需更精细化登录用户，可解 JWT 后另算配额，默认先按 IP 够起步用）
    key = _ip_key(request)
    if not _rl_ip.check(key, 12):  # 每 IP 每分钟 12 次，适度宽松
        raise HTTPException(status_code=429, detail="提问太频繁啦，请稍后再试（每分钟最多 12 次）")

    # 2) history 长度保护
    history: list[dict] = [m.model_dump() for m in (req.history or [])]
    if len(history) > 20:
        history = history[-20:]

    # 3) 调业务
    t0 = time.perf_counter()
    result: ConsultReply = await consult(req.message, history)
    dt_ms = int((time.perf_counter() - t0) * 1000)

    log.info("consult chat %s | len=%d | src=%s | hits=%s | %dms",
             key, len(req.message), result.source, ",".join(result.hits[:3]), dt_ms)

    return ChatResponse(reply=result.reply, source=result.source,
                        hits=result.hits, latency_ms=dt_ms)


@router.get("/majors", response_model=list[MajorItemOut])
def search_majors(q: str = "", limit: int = 10):
    """前端输入联想/参考专业搜索。q 为空返回热门 10 个。"""
    limit = min(max(1, limit), 50)
    cat = get_catalog()
    q = (q or "").strip()
    if q:
        hits = cat.search(q, top_k=limit)
    else:
        # 返回热门（选几个高薪/热门关键词优先）
        hot_keys = ["计算机", "人工智能", "法学", "临床医学", "口腔医学",
                    "金融", "电子", "电气", "自动化", "软件工程"]
        hits_map: dict[str, Any] = {}
        for k in hot_keys:
            for it in cat.search(k, top_k=3):
                if it.code not in hits_map:
                    hits_map[it.code] = it
                if len(hits_map) >= limit:
                    break
            if len(hits_map) >= limit:
                break
        hits = list(hits_map.values())[:limit]

    return [MajorItemOut(
        code=it.code, name=it.name, cat=it.cat, cat2=it.cat2,
        degree=it.degree, years=it.years, tags=list(it.tags), note=it.note,
    ) for it in hits]
