# routers/auth.py —— 注册/登录/JWT + 考生信息持久化（第15步）
# MySQL 没装也没关系：db/base 会回退到 SQLite（logs/dev.sqlite3），保证本地跑通。

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import app as app_cfg
from db.base import Base, engine, get_db
from db.models import StudentProfile, User
from services.pwd_hasher import hash_password, verify_password

log = logging.getLogger(__name__)

# 启动时自动建表（SQLite 100% 成功，MySQL 若数据库不存在会报错，但后续操作仍可用）
try:
    Base.metadata.create_all(bind=engine)
    log.info("DB tables created (users / student_profiles).")
except Exception as e:
    log.warning("DB create_all 失败（通常是 MySQL 还没建好库）：%s", e)

router = APIRouter()
BJR = timezone(timedelta(hours=8))  # 北京时间


# ---------------- 请求/响应模型 ----------------
class RegisterReq(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class LoginReq(BaseModel):
    username: str
    password: str


class TokenResp(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_in: int  # 分钟
    user_id: int
    username: str


class Profile(BaseModel):
    province: Optional[str] = None
    subjects: list[str] = []
    score: Optional[int] = None
    school: Optional[str] = None
    region: Optional[str] = None
    major: Optional[str] = None
    strategy: Optional[str] = None
    gradPlan: Optional[str] = None
    career: Optional[str] = None
    tuition: Optional[str] = None


# ---------------- JWT 工具 ----------------
def _issue_token(user_id: int, username: str) -> tuple[str, int]:
    exp_min = max(1, int(app_cfg.JWT_EXPIRE_MINUTES))
    exp = datetime.now(BJR) + timedelta(minutes=exp_min)
    payload = {"sub": user_id, "name": username, "exp": exp}
    token = jwt.encode(payload, app_cfg.SECRET_KEY, algorithm="HS256")
    return token, exp_min


# ---------------- 接口 ----------------
@router.post("/register")
def register(body: RegisterReq, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == body.username).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在")
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token, exp = _issue_token(user.id, user.username)
    return TokenResp(token=token, expires_in=exp, user_id=user.id, username=user.username)


@router.post("/login")
def login(body: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    token, exp = _issue_token(user.id, user.username)
    return TokenResp(token=token, expires_in=exp, user_id=user.id, username=user.username)


# ----- 登录后：保存/获取考生信息（一次填写，长期保存） -----
# 从 Header.Authorization 里取 Bearer token
def _current_user(authorization: Optional[str] = Header(default=None),
                  db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "缺少 Token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, app_cfg.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token 无效或已过期")
    user_id: int = payload.get("sub")  # type: ignore[assignment]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user


def _profile_to_dict(p: Optional[StudentProfile]) -> dict:
    if not p:
        return {"province": None, "subjects": [], "score": None,
                "school": None, "region": None, "major": None,
                "strategy": None, "gradPlan": None, "career": None, "tuition": None}
    subs: list[str] = []
    if p.subjects:
        try:
            subs = json.loads(p.subjects)
            if not isinstance(subs, list):
                subs = []
        except Exception:
            subs = [s for s in p.subjects.split(",") if s]
    return {
        "province": p.province,
        "subjects": subs,
        "score": p.score,
        "school": p.school,
        "region": p.region,
        "major": p.major,
        "strategy": p.strategy,
        "gradPlan": p.grad_plan,
        "career": p.career,
        "tuition": p.tuition,
    }


@router.get("/profile")
def get_profile(user: User = Depends(_current_user),
                db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    return {"username": user.username, "profile": _profile_to_dict(profile)}


@router.put("/profile")
def save_profile(body: Profile,
                 user: User = Depends(_current_user),
                 db: Session = Depends(get_db)):
    p = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    data = body.model_dump()
    if p is None:
        p = StudentProfile(user_id=user.id)
        db.add(p)
    p.province = data["province"]
    p.subjects = json.dumps(data["subjects"] or [], ensure_ascii=False)
    p.score = data["score"]
    p.school = data["school"]
    p.region = data["region"]
    p.major = data["major"]
    p.strategy = data["strategy"]
    p.grad_plan = data["gradPlan"]
    p.career = data["career"]
    p.tuition = data["tuition"]
    try:
        p.extra = json.dumps(data, ensure_ascii=False)
    except Exception:
        pass
    db.commit()
    db.refresh(p)
    return {"ok": True, "profile": _profile_to_dict(p)}
