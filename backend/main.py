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
from .models import Settings, EmailHistory, DEFAULT_ACCOUNT_TEMPLATE, DEFAULT_SUBSCRIPTION_TEMPLATE
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
    smtp_host: str = "mail.21vianet.com"
    smtp_port: int = 587
    email_address: str = ""
    password: str = ""
    account_template: str = DEFAULT_ACCOUNT_TEMPLATE
    subscription_template: str = DEFAULT_SUBSCRIPTION_TEMPLATE


class SettingsResponse(BaseModel):
    smtp_host: str
    smtp_port: int
    email_address: str
    password_masked: str
    account_template: str
    subscription_template: str
    updated_at: str | None


class SubscriptionItem(BaseModel):
    subscription_id: str
    subscription_name: str


class SendEmailRequest(BaseModel):
    email_type: str = Field(..., pattern="^(account|subscription)$")
    recipient: str
    cc: str = ""
    subject: str = ""
    body: str = ""
    # account type fields
    account: str | None = None
    password: str | None = None
    account_type: str | None = None
    # subscription type fields
    subscriptions: list[SubscriptionItem] = []
    remark: str = ""


class HistoryResponse(BaseModel):
    id: int
    email_type: str
    recipient: str
    cc: str
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
        return SettingsResponse(
            smtp_host="mail.21vianet.com",
            smtp_port=587,
            email_address="",
            password_masked="",
            account_template=DEFAULT_ACCOUNT_TEMPLATE,
            subscription_template=DEFAULT_SUBSCRIPTION_TEMPLATE,
            updated_at=None,
        )
    return SettingsResponse(
        smtp_host=s.smtp_host or "mail.21vianet.com",
        smtp_port=s.smtp_port or 587,
        email_address=s.email_address or "",
        password_masked="********" if s.encrypted_password else "",
        account_template=s.account_template or DEFAULT_ACCOUNT_TEMPLATE,
        subscription_template=s.subscription_template or DEFAULT_SUBSCRIPTION_TEMPLATE,
        updated_at=s.updated_at.isoformat() if s.updated_at else None,
    )


@app.post("/api/settings")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    if not s:
        s = Settings()
        db.add(s)
    s.smtp_host = payload.smtp_host
    s.smtp_port = payload.smtp_port
    s.email_address = payload.email_address
    s.account_template = payload.account_template
    s.subscription_template = payload.subscription_template
    if payload.password:
        s.encrypted_password = encrypt_password(payload.password)
    s.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ── Template rendering ──────────────────────────────────


def render_account_body(template: str, data: SendEmailRequest) -> str:
    return template.replace("{account}", data.account or "") \
                   .replace("{password}", data.password or "") \
                   .replace("{account_type}", data.account_type or "") \
                   .replace("{remark}", data.remark or "")


def render_subscription_body(template: str, data: SendEmailRequest) -> str:
    lines = []
    for i, sub in enumerate(data.subscriptions, 1):
        lines.append(f"  {i}. {sub.subscription_id} - {sub.subscription_name}")
    subscription_list = "\n".join(lines) if lines else "（无）"
    return template.replace("{subscription_list}", subscription_list) \
                   .replace("{remark}", data.remark or "")


# ── Send Email API ──────────────────────────────────────


@app.post("/api/send")
def send_email_api(data: SendEmailRequest, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    if not s or not s.email_address or not s.encrypted_password:
        raise HTTPException(status_code=400, detail="请先在设置中配置邮箱凭据")

    smtp_password = decrypt_password(s.encrypted_password)

    if data.email_type == "account":
        if not data.account or not data.password or not data.account_type:
            raise HTTPException(status_code=400, detail="请填写账号、密码和账户类型")
        template = s.account_template or DEFAULT_ACCOUNT_TEMPLATE
        body = render_account_body(template, data)
    else:
        if not data.subscriptions:
            raise HTTPException(status_code=400, detail="请至少添加一条订阅")
        template = s.subscription_template or DEFAULT_SUBSCRIPTION_TEMPLATE
        body = render_subscription_body(template, data)

    success, error_msg = send_email(
        smtp_host=s.smtp_host,
        smtp_port=s.smtp_port,
        email_address=s.email_address,
        password=smtp_password,
        recipient=data.recipient,
        subject=data.subject,
        body=body,
        cc=data.cc,
    )

    record = EmailHistory(
        email_type=data.email_type,
        recipient=data.recipient,
        cc=data.cc,
        subject=data.subject,
        body=body,
        status="success" if success else "failed",
        error_message=error_msg,
    )
    db.add(record)
    db.commit()

    if not success:
        raise HTTPException(status_code=500, detail=error_msg)

    return {"ok": True, "history_id": record.id}


# ── History APIs ───────────────────────────────────────


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
                cc=item.cc or "",
                subject=item.subject or "",
                status=item.status,
                error_message=item.error_message or "",
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


# ── Frontend static serving (production mode) ───────────

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str, request: Request):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.exists():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
