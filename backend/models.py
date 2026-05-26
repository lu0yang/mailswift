from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime
from .database import Base


DEFAULT_ACCOUNT_TEMPLATE = """您好，

您的账号已创建完成，信息如下：
  账号：{account}
  密码：{password}
  类型：{account_type}
{remark}"""

DEFAULT_SUBSCRIPTION_TEMPLATE = """您好，

您的订阅已创建完成，信息如下：
{subscription_list}
{remark}"""


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    smtp_host = Column(String(255), default="mail.21vianet.com")
    smtp_port = Column(Integer, default=587)
    email_address = Column(String(255), default="")
    encrypted_password = Column(Text, default="")
    account_template = Column(Text, default=DEFAULT_ACCOUNT_TEMPLATE)
    subscription_template = Column(Text, default=DEFAULT_SUBSCRIPTION_TEMPLATE)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


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
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
