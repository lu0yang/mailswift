import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import init_db, get_db
from .models import Settings, EmailHistory
from .crypto_utils import encrypt_password, decrypt_password
from .mail_sender import send_email

# Resolve frontend dist path
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="MailSwift", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic schemas ────────────────────────────────────


class SettingsUpdate(BaseModel):
    email_address: str
    password: str


class SettingsResponse(BaseModel):
    email_address: str
    password_masked: str
    updated_at: str | None


class SendEmailRequest(BaseModel):
    email_type: str = Field(..., pattern="^(account|subscription)$")
    recipient: str
    account: str | None = None          # for account type
    password: str | None = None          # for account type (the target account password, not SMTP)
    account_type: str | None = None      # for account type
    subscription_id: str | None = None   # for subscription type
    subscription_name: str | None = None # for subscription type
    subscription_type: str | None = None # for subscription type
    remark: str = ""


class HistoryResponse(BaseModel):
    id: int
    email_type: str
    recipient: str
    subject: str
    status: str
    error_message: str
    sent_at: str


class HistoryListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[HistoryResponse]


# ── Settings APIs ───────────────────────────────────────


@app.get("/api/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    if not s:
        return SettingsResponse(email_address="", password_masked="", updated_at=None)
    return SettingsResponse(
        email_address=s.email_address,
        password_masked="********" if s.encrypted_password else "",
        updated_at=s.updated_at.isoformat() if s.updated_at else None,
    )


@app.post("/api/settings")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    if not s:
        s = Settings()
        db.add(s)
    s.email_address = payload.email_address
    s.encrypted_password = encrypt_password(payload.password)
    s.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ── Send Email API ──────────────────────────────────────


def build_account_email(data: SendEmailRequest) -> tuple[str, str]:
    subject = "您的账号已创建完成"
    lines = [
        "您好，",
        "",
        "您的账号已创建完成，信息如下：",
        f"  账号：{data.account}",
        f"  密码：{data.password}",
        f"  类型：{data.account_type}",
    ]
    if data.remark:
        lines.append(f"\n{data.remark}")
    return subject, "\n".join(lines)


def build_subscription_email(data: SendEmailRequest) -> tuple[str, str]:
    subject = "您的订阅已创建完成"
    lines = [
        "您好，",
        "",
        "您的订阅已创建完成，信息如下：",
        f"  订阅 ID：{data.subscription_id}",
        f"  订阅名称：{data.subscription_name}",
        f"  订阅类型：{data.subscription_type}",
    ]
    if data.remark:
        lines.append(f"\n{data.remark}")
    return subject, "\n".join(lines)


@app.post("/api/send")
def send_email_api(data: SendEmailRequest, db: Session = Depends(get_db)):
    # Load SMTP credentials
    s = db.query(Settings).first()
    if not s or not s.email_address or not s.encrypted_password:
        raise HTTPException(status_code=400, detail="请先在设置中配置邮箱凭据")

    smtp_password = decrypt_password(s.encrypted_password)

    # Build email content
    if data.email_type == "account":
        if not data.account or not data.password or not data.account_type:
            raise HTTPException(status_code=400, detail="账号类型邮件需要填写账号、密码和账户类型")
        subject, body = build_account_email(data)
    else:
        if not data.subscription_id or not data.subscription_name or not data.subscription_type:
            raise HTTPException(status_code=400, detail="订阅类型邮件需要填写订阅ID、订阅名称和订阅类型")
        subject, body = build_subscription_email(data)

    # Send
    success, error_msg = send_email(
        smtp_host=s.smtp_host,
        smtp_port=s.smtp_port,
        email_address=s.email_address,
        password=smtp_password,
        recipient=data.recipient,
        subject=subject,
        body=body,
    )

    # Record history
    record = EmailHistory(
        email_type=data.email_type,
        recipient=data.recipient,
        subject=subject,
        body=body,
        status="success" if success else "failed",
        error_message=error_msg,
    )
    db.add(record)
    db.commit()

    if not success:
        raise HTTPException(status_code=500, detail=error_msg)

    return {"ok": True, "history_id": record.id}


# ── History APIs ────────────────────────────────────────


@app.get("/api/history", response_model=HistoryListResponse)
def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    email_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(EmailHistory)
    if email_type:
        q = q.filter(EmailHistory.email_type == email_type)

    total = q.count()
    items = (
        q.order_by(EmailHistory.sent_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return HistoryListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            HistoryResponse(
                id=item.id,
                email_type=item.email_type,
                recipient=item.recipient,
                subject=item.subject,
                status=item.status,
                error_message=item.error_message,
                sent_at=item.sent_at.isoformat() if item.sent_at else "",
            )
            for item in items
        ],
    )


@app.delete("/api/history/{record_id}")
def delete_history(record_id: int, db: Session = Depends(get_db)):
    record = db.query(EmailHistory).filter(EmailHistory.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Frontend static serving (production mode) ─────────────

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str, request: Request):
        """Serve Vue SPA — return index.html for all non-API routes."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.exists():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
