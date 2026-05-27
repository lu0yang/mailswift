from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from .database import Base


DEFAULT_ACCOUNT_TEMPLATE = """您好，

您的账号已创建完成，信息如下：

{account_list}

如有任何疑问，请联系 IT 支持团队。"""

DEFAULT_SUBSCRIPTION_TEMPLATE = """您好，

您的订阅已创建完成，信息如下：

{subscription_list}

如有任何疑问，请联系 IT 支持团队。"""


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    smtp_host = Column(String(255), default="mail.21vianet.com")
    smtp_port = Column(Integer, default=587)
    email_address = Column(String(255), default="")
    encrypted_password = Column(Text, default="")
    imap_host = Column(String(255), default="partner.outlook.cn")
    imap_port = Column(Integer, default=993)
    account_template = Column(Text, default="")
    subscription_template = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    content = Column(Text, default="")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Signature(Base):
    __tablename__ = "signatures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    content = Column(Text, default="")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmailHistory(Base):
    __tablename__ = "email_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_type = Column(String(50), nullable=False)
    recipient = Column(String(255), nullable=False)
    cc = Column(String(500), default="")
    subject = Column(String(500), default="")
    body = Column(Text, default="")
    status = Column(String(20), nullable=False)
    error_message = Column(Text, default="")
    archive_status = Column(String(20), default="")
    template_id = Column(Integer, nullable=True)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
