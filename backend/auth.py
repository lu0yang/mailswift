"""
用户身份处理。

- 同事网站跳转时通过 X-User-Id header 传入用户身份
- 独立使用时（无 X-User-Id），自动使用默认用户，保持后向兼容
"""

import logging

from fastapi import Request, Depends
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

logger = logging.getLogger(__name__)


def get_or_create_user(db: Session, external_id: str | None) -> User:
    """根据 external_id 查找或创建用户，返回 User 对象。"""
    if external_id:
        user = db.query(User).filter(User.external_id == external_id).first()
        if not user:
            user = User(external_id=external_id)
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("新用户注册: external_id=%s, internal_id=%s", external_id, user.id)
        return user

    # 无 X-User-Id：独立使用模式，返回默认用户
    user = db.query(User).filter(User.external_id.is_(None)).first()
    if not user:
        user = User(external_id=None, display_name="默认用户")
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("创建默认用户: id=%s", user.id)
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI 依赖注入：从请求中解析当前用户。"""
    external_id = request.headers.get("X-User-Id")
    return get_or_create_user(db, external_id)
