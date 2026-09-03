# config.py —— 集中配置（从 .env 读取）
# step14：所有密钥/环境变量只在这里加载，其它模块从 config 取

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 工作区根目录：backend/..
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE, override=True)


class LLMConfig:
    API_KEY: str = os.getenv("LLM_API_KEY", "").strip()
    BASE_URL: str = os.getenv(
        "LLM_BASE_URL", "https://api.deepseek.com/v1"
    ).strip().rstrip("/")
    MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat").strip()
    TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))
    # 没配 Key 时，不调用真 LLM，fallback 到 mock（第13步"先免费测试"）
    ENABLED: bool = bool(API_KEY)


class MySQLConfig:
    HOST: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    USER: str = os.getenv("MYSQL_USER", "root")
    PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    DATABASE: str = os.getenv("MYSQL_DATABASE", "zhiyuan")
    CHARSET: str = "utf8mb4"

    @classmethod
    def dsn(cls) -> str:
        return (
            f"mysql+pymysql://{cls.USER}:{cls.PASSWORD}"
            f"@{cls.HOST}:{cls.PORT}/{cls.DATABASE}?charset={cls.CHARSET}"
        )


class AppConfig:
    SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "change-me-in-prod-!2026").strip()
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24 * 7)))  # 默认 7 天（分钟）
    # 服务日志目录（第16步：控制台 + 定时写盘）
    LOG_DIR: Path = BASE_DIR / "logs"
    LOG_DIR.mkdir(exist_ok=True)


# 便捷别名
llm = LLMConfig()
mysql = MySQLConfig()
app = AppConfig()
