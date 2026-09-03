# 「智愿」AI 高考志愿填报 App

> 面向高考考生与家长设计的双功能 AI 产品：① 志愿方案生成 ② 高考专业 AI 顾问问答。独立完成从需求调研→PRD→原型→前后端→LLM接入→知识库→登录系统→限流日志→云端部署的 17 步工程化全流程。

## ✨ 功能亮点

| 模块 | 说明 |
|------|------|
| 🧑‍🎓 **填报方案** | 考生省份/选科/成绩 + 偏好策略 → DeepSeek LLM → 冲/稳/保/备 四级结构化志愿卡片 |
| 🎓 **AI 专业顾问** | 专业课程/就业前景/考研发展/选科要求 8 类问答 + 越界拒答三重兜底 + 教育部 12×292 专业知识库（RAG 雏形） |
| 👤 **账号系统** | 注册/登录（JWT + bcrypt）→ 考生信息一键自动回填，MySQL/SQLite 双引擎自动兜底 |
| 🛡️ **三高架构** | FastAPI 三层拆分 + 单 IP 限流 + LLM 超时 Mock 回退 + 日志按时间切分写盘 + start_server.bat 一键启动 |

## 🛠️ 技术栈

- **后端**：Python、FastAPI、SQLAlchemy、PyMySQL / SQLite、JWT、bcrypt、httpx、python-dotenv
- **LLM**：DeepSeek 云端 LLM（OpenAI 兼容协议）+ 自建结构化专业知识库 + 越界拒答三重兜底
- **前端**：原生 HTML + CSS + JavaScript（单页 Tab 切换，0 构建依赖）；数据分离（data.js / test_data.js）+ 配置分离（.env）
- **部署**：Gunicorn + Nginx + 云服务器（2C2G），支持 6-7 月高峰横向扩容

## 🚀 本地 1 分钟启动

```bash
# 1. 安装依赖（Python 3.10+）
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# 2. 配置密钥
copy .env.example .env
# 编辑 .env，填写 LLM_API_KEY=sk-xxx （你的 DeepSeek Key）

# 3. 一键启动（Windows）
双击 backend\start_server.bat

# 4. 打开浏览器
# 填报方案 & 专业顾问：http://127.0.0.1:8000
# 健康检查 & Key 验证：http://127.0.0.1:8000/api/health
```

## 📂 项目结构

```
zhiyuan/
├── .env / .env.example          # 密钥配置（不进仓库）
├── backend/
│   ├── main.py                  # FastAPI 入口 + 日志中间件
│   ├── config.py                # .env 统一加载
│   ├── schemas.py               # Pydantic 请求/响应模型
│   ├── routers/                 # auth（登录）/ consult（专业顾问 )
│   ├── services/                # llm_client / plan_service / consult_service / pwd_hasher
│   ├── data/                    # mock_plan + undergraduate_majors.json + major_catalog.py
│   ├── db/                      # base（双引擎）+ models（User/考生信息表）
│   ├── requirements.txt
│   ├── start_server.bat         # Windows 一键启动（自动清端口）
│   └── 云端部署手册.md           # 云服务器+Nginx 部署步骤
├── zhiyuan_app.html             # 前端单页（填报方案 Tab / 专业顾问 Tab）
├── data.js / test_data.js       # 静态/动态数据分离
├── 高考志愿PRD.md / 后端架构设计.md / 需求调研.md / 高考志愿线框图.html
```

## ⚠️ 公开仓库前必读（2 条红线）

1. **确认 `.gitignore` 在仓库根目录且生效** → 别把 `.env`（你的 DeepSeek Key）、`jianli/*.docx`（你的姓名/学校/手机隐私）、`.venv/`（50000+ 依赖）传上去！
2. **真实用户数据别传** → `backend/data/*.db` / `*.sqlite`（含用户注册信息哈希）不要进公开仓库。


## 📄 许可证

个人学习用途，使用请注明来源。
