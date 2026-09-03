# db/base.py —— SQLAlchemy 引擎、Session、Base（第15步）
# 未配置有效 MySQL 或依赖缺失时，回退到 SQLite 内存库，保证开发时可启动。

from __future__ import annotations

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import mysql as cfg

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _build_engine():
    """优先使用 MySQL；连不上时自动回退到 SQLite（内存/文件），方便本地开发。"""
    try:
        if cfg.PASSWORD and cfg.DATABASE:
            engine = create_engine(cfg.dsn(), pool_pre_ping=True, pool_recycle=3600, echo=False)
            # 轻量探活：只是 build，不真的 open connection 做测试
            log.info("DB engine: MySQL %s@%s:%s/%s", cfg.USER, cfg.HOST, cfg.PORT, cfg.DATABASE)
            return engine
    except Exception as e:
        log.warning("MySQL engine 初始化失败（可以忽略，下面回退 SQLite）：%s", e)
    from pathlib import Path

    fallback = Path(__file__).resolve().parent.parent.parent / "logs" / "dev.sqlite3"
    fallback.parent.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{fallback}", echo=False, future=True)
    log.warning("DB engine: FALLBACK SQLite at %s", fallback)
    return engine


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
