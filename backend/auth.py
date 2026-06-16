"""
用户认证模块

- 独立登录: email + password → JWT
- 同事跳转: email + api_key → JWT（服务器间调用）
- API 鉴权: 从 Authorization header 解析 JWT
"""

import hashlib
import os
import logging
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session

from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS, AUTO_LOGIN_API_KEY
from .database import get_db
from .models import User

logger = logging.getLogger(__name__)

_TZ = timezone(timedelta(hours=8))


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 哈希密码。"""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否匹配哈希值。"""
    try:
        salt_hex, key_hex = hashed.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return new_key == key
    except Exception:
        return False


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


def login_user(db: Session, email: str, password: str) -> str | None:
    """邮箱+密码登录，成功返回 JWT，失败返回 None。"""
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.updated_at = datetime.now(_TZ)
    db.commit()
    return create_jwt(user.id, user.email)


def auto_login_user(db: Session, email: str, api_key: str) -> str | None:
    """
    同事系统自动登录：验证 api_key + 查/建用户，返回 JWT。
    api_key 不匹配返回 None。
    """
    if api_key != AUTO_LOGIN_API_KEY:
        return None

    user = db.query(User).filter(User.email == email).first()
    if not user:
        display_name = email.split("@")[0] if "@" in email else email
        user = User(email=email, display_name=display_name)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("自动注册用户: email=%s, id=%s", email, user.id)

    user.updated_at = datetime.now(_TZ)
    db.commit()
    return create_jwt(user.id, user.email)


def register_user(db: Session, email: str, password: str) -> str | None:
    """用户自助注册，邮箱已存在则返回 None。"""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None
    display_name = email.split("@")[0] if "@" in email else email
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_jwt(user.id, user.email)
