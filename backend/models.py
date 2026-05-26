from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime
from .database import Base


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    smtp_host = Column(String(255), default="smtp.office365.com")
    smtp_port = Column(Integer, default=587)
    email_address = Column(String(255), default="")
    encrypted_password = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class EmailHistory(Base):
    __tablename__ = "email_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_type = Column(String(50), nullable=False)  # 'account' | 'subscription'
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), default="")
    body = Column(Text, default="")
    status = Column(String(20), nullable=False)  # 'success' | 'failed'
    error_message = Column(Text, default="")
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
