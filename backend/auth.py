"""
用户认证模块

登录：email + password → 连 EWS 验证 → 签发 JWT
后续请求：Authorization header 携带 JWT → 验签即可
密码不存数据库，仅在浏览器 sessionStorage 中保留本次会话。
"""

import logging
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session

from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS
from .database import get_db
from .models import User
from .mail_sender import verify_connection

logger = logging.getLogger(__name__)
_TZ = timezone(timedelta(hours=8))


def create_jwt(user_id: int, email: str) -> str:
    """签发 JWT Token。"""
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict | None:
    """解析 JWT，失败返回 None。"""
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except pyjwt.PyJWTError:
        return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI 依赖：从 Authorization header 解析当前用户。"""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")

    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user


def login_or_register(db: Session, email: str, password: str) -> str | None:
    """
    登录/注册：用 email + password 连接 EWS 验证身份。
    成功则查找或创建用户，返回 JWT。
    失败返回 None。
    """
    success, _ = verify_connection(email, password)
    if not success:
        return None

    user = db.query(User).filter(User.email == email).first()
    if not user:
        display_name = email.split("@")[0] if "@" in email else email
        user = User(email=email, display_name=display_name)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("新用户注册: email=%s, id=%s", email, user.id)

    user.updated_at = datetime.now(_TZ)
    db.commit()
    return create_jwt(user.id, user.email)
