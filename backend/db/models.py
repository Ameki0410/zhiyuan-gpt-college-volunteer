# db/models.py —— 用户表、考生信息表（第15步）

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class StudentProfile(Base):
    """考生填一次即可的信息，登录后回传到前端，下次不用重复填写。"""
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(32), nullable=True)
    subjects: Mapped[str] = mapped_column(String(128), nullable=True)  # JSON 数组字符串
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    # 偏好字段
    school: Mapped[str] = mapped_column(String(64), nullable=True)
    region: Mapped[str] = mapped_column(String(64), nullable=True)
    major: Mapped[str] = mapped_column(String(64), nullable=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=True)
    grad_plan: Mapped[str] = mapped_column(String(32), nullable=True)
    career: Mapped[str] = mapped_column(String(64), nullable=True)
    tuition: Mapped[str] = mapped_column(String(16), nullable=True)
    # 兜底：序列化后的完整表单 JSON（如果未来加字段不迁移也能保存）
    extra: Mapped[str] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
