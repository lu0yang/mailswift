import logging
import re
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import markdown
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import init_db, get_db
from .models import (
    Settings, EmailHistory, EmailTemplate, Signature,
    DEFAULT_ACCOUNT_TEMPLATE, DEFAULT_SUBSCRIPTION_TEMPLATE,
)
from .crypto_utils import encrypt_password, decrypt_password
from .mail_sender import send_email
from .imap_saver import save_to_sent_items

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _migrate_schema(db: Session):
    """Add columns that may be missing from older DB versions."""
    import sqlalchemy as sa
    insp = sa.inspect(db.get_bind())

    # settings table
    settings_cols = {c["name"] for c in insp.get_columns("settings")}
    if "imap_host" not in settings_cols:
        db.execute(sa.text("ALTER TABLE settings ADD COLUMN imap_host VARCHAR(255) DEFAULT 'partner.outlook.cn'"))
        db.execute(sa.text("UPDATE settings SET imap_host = 'partner.outlook.cn' WHERE imap_host IS NULL"))
    if "imap_port" not in settings_cols:
        db.execute(sa.text("ALTER TABLE settings ADD COLUMN imap_port INTEGER DEFAULT 993"))
        db.execute(sa.text("UPDATE settings SET imap_port = 993 WHERE imap_port IS NULL"))

    # email_history table
    if "email_history" in insp.get_table_names():
        history_cols = {c["name"] for c in insp.get_columns("email_history")}
        if "archive_status" not in history_cols:
            db.execute(sa.text("ALTER TABLE email_history ADD COLUMN archive_status VARCHAR(20) DEFAULT ''"))
        if "template_id" not in history_cols:
            db.execute(sa.text("ALTER TABLE email_history ADD COLUMN template_id INTEGER"))

    db.commit()


def _migrate_templates(db: Session):
    """Migrate legacy Settings template fields into email_templates table."""
    existing = db.query(EmailTemplate).count()
    if existing > 0:
        return

    s = db.query(Settings).first()
    account_content = DEFAULT_ACCOUNT_TEMPLATE
    sub_content = DEFAULT_SUBSCRIPTION_TEMPLATE
    if s:
        if s.account_template:
            account_content = s.account_template
        if s.subscription_template:
            sub_content = s.subscription_template

    db.add(EmailTemplate(name="默认账号模板", type="account", content=account_content))
    db.add(EmailTemplate(name="默认订阅模板", type="subscription", content=sub_content))
    db.commit()
    logger.info("Migrated legacy templates to email_templates table")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = next(get_db())
    try:
        _migrate_schema(db)
        _migrate_templates(db)
    finally:
        db.close()
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
    imap_host: str = "partner.outlook.cn"
    imap_port: int = 993


class SettingsResponse(BaseModel):
    smtp_host: str
    smtp_port: int
    email_address: str
    password_masked: str
    imap_host: str
    imap_port: int
    updated_at: str | None


class AccountItem(BaseModel):
    account: str
    password: str
    account_type: str


class SubscriptionItem(BaseModel):
    subscription_id: str
    subscription_name: str


class SendEmailRequest(BaseModel):
    email_type: str = Field(..., pattern="^(account|subscription)$")
    recipient: str
    cc: str = ""
    subject: str = ""
    body: str = ""
    template_id: int | None = None
    signature_id: int | None = None
    accounts: list[AccountItem] = []
    subscriptions: list[SubscriptionItem] = []


class HistoryResponse(BaseModel):
    id: int
    email_type: str
    recipient: str
    cc: str
    subject: str
    status: str
    error_message: str
    archive_status: str
    sent_at: str


class HistoryListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[HistoryResponse]


class TemplateCreate(BaseModel):
    name: str
    type: str = Field(..., pattern="^(account|subscription)$")
    content: str = ""


class TemplateUpdate(BaseModel):
    name: str
    content: str


class TemplateResponse(BaseModel):
    id: int
    name: str
    type: str
    content: str
    created_at: str


class SignatureCreate(BaseModel):
    name: str
    content: str = ""
    is_default: bool = False


class SignatureUpdate(BaseModel):
    name: str
    content: str
    is_default: bool = False


class SignatureResponse(BaseModel):
    id: int
    name: str
    content: str
    is_default: bool
    created_at: str


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
            imap_host="partner.outlook.cn",
            imap_port=993,
            updated_at=None,
        )
    return SettingsResponse(
        smtp_host=s.smtp_host or "mail.21vianet.com",
        smtp_port=s.smtp_port or 587,
        email_address=s.email_address or "",
        password_masked="********" if s.encrypted_password else "",
        imap_host=s.imap_host or "partner.outlook.cn",
        imap_port=s.imap_port or 993,
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
    s.imap_host = payload.imap_host
    s.imap_port = payload.imap_port
    if payload.password:
        s.encrypted_password = encrypt_password(payload.password)
    s.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


class TestSmtpRequest(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 587
    email_address: str = ""
    password: str = ""


@app.post("/api/settings/test-smtp")
def test_smtp(data: TestSmtpRequest = TestSmtpRequest(), db: Session = Depends(get_db)):
    s = db.query(Settings).first()

    # Use request body params if provided, otherwise fall back to saved settings
    if data.email_address and data.password:
        host = data.smtp_host or "mail.21vianet.com"
        port = data.smtp_port or 587
        addr = data.email_address
        pwd = data.password
    elif s and s.email_address and s.encrypted_password:
        host = s.smtp_host
        port = s.smtp_port
        addr = s.email_address
        pwd = decrypt_password(s.encrypted_password)
    else:
        raise HTTPException(status_code=400, detail="请先填写邮箱地址和密码")

    success, error_msg, _ = send_email(
        smtp_host=host,
        smtp_port=port,
        email_address=addr,
        password=pwd,
        recipient=addr,
        subject="MailSwift 连接测试",
        body_html="<p>这是一封测试邮件，用于验证 SMTP 配置是否正确。</p>",
        body_plain="这是一封测试邮件，用于验证 SMTP 配置是否正确。",
    )
    if not success:
        raise HTTPException(status_code=400, detail=error_msg)
    return {"ok": True}


# ── Template CRUD ───────────────────────────────────────


@app.get("/api/templates", response_model=list[TemplateResponse])
def list_templates(
    type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(EmailTemplate)
    if type:
        q = q.filter(EmailTemplate.type == type)
    items = q.order_by(EmailTemplate.created_at.desc()).all()
    return [
        TemplateResponse(
            id=t.id, name=t.name, type=t.type, content=t.content,
            created_at=t.created_at.isoformat() if t.created_at else "",
        )
        for t in items
    ]


@app.post("/api/templates", response_model=TemplateResponse)
def create_template(data: TemplateCreate, db: Session = Depends(get_db)):
    t = EmailTemplate(name=data.name, type=data.type, content=data.content)
    db.add(t)
    db.commit()
    db.refresh(t)
    return TemplateResponse(
        id=t.id, name=t.name, type=t.type, content=t.content,
        created_at=t.created_at.isoformat() if t.created_at else "",
    )


@app.put("/api/templates/{template_id}", response_model=TemplateResponse)
def update_template(template_id: int, data: TemplateUpdate, db: Session = Depends(get_db)):
    t = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    t.name = data.name
    t.content = data.content
    db.commit()
    db.refresh(t)
    return TemplateResponse(
        id=t.id, name=t.name, type=t.type, content=t.content,
        created_at=t.created_at.isoformat() if t.created_at else "",
    )


@app.delete("/api/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    t = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ── Signature CRUD ──────────────────────────────────────


@app.get("/api/signatures", response_model=list[SignatureResponse])
def list_signatures(db: Session = Depends(get_db)):
    items = db.query(Signature).order_by(Signature.created_at.desc()).all()
    return [
        SignatureResponse(
            id=s.id, name=s.name, content=s.content,
            is_default=s.is_default,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in items
    ]


@app.post("/api/signatures", response_model=SignatureResponse)
def create_signature(data: SignatureCreate, db: Session = Depends(get_db)):
    if data.is_default:
        db.query(Signature).filter(Signature.is_default == True).update({"is_default": False})  # noqa: E712
    s = Signature(name=data.name, content=data.content, is_default=data.is_default)
    db.add(s)
    db.commit()
    db.refresh(s)
    return SignatureResponse(
        id=s.id, name=s.name, content=s.content,
        is_default=s.is_default,
        created_at=s.created_at.isoformat() if s.created_at else "",
    )


@app.put("/api/signatures/{signature_id}", response_model=SignatureResponse)
def update_signature(signature_id: int, data: SignatureUpdate, db: Session = Depends(get_db)):
    s = db.query(Signature).filter(Signature.id == signature_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="签名不存在")
    if data.is_default:
        db.query(Signature).filter(Signature.is_default == True).update({"is_default": False})  # noqa: E712
    s.name = data.name
    s.content = data.content
    s.is_default = data.is_default
    db.commit()
    db.refresh(s)
    return SignatureResponse(
        id=s.id, name=s.name, content=s.content,
        is_default=s.is_default,
        created_at=s.created_at.isoformat() if s.created_at else "",
    )


@app.delete("/api/signatures/{signature_id}")
def delete_signature(signature_id: int, db: Session = Depends(get_db)):
    s = db.query(Signature).filter(Signature.id == signature_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="签名不存在")
    db.delete(s)
    db.commit()
    return {"ok": True}


# ── Template rendering ──────────────────────────────────


def render_account_list(accounts: list[AccountItem]) -> str:
    lines = []
    for i, acct in enumerate(accounts, 1):
        lines.append(f"{i}. {acct.account} / {acct.password} / {acct.account_type}")
    return "\n".join(lines) if lines else "（无）"


def render_subscription_list(subs: list[SubscriptionItem]) -> str:
    lines = []
    for i, sub in enumerate(subs, 1):
        lines.append(f"{i}. {sub.subscription_id} - {sub.subscription_name}")
    return "\n".join(lines) if lines else "（无）"


def render_body(template_content: str, data: SendEmailRequest) -> str:
    """Substitute template variables into the markdown body."""
    if data.email_type == "account":
        body = template_content.replace("{account_list}", render_account_list(data.accounts))
    else:
        body = template_content.replace("{subscription_list}", render_subscription_list(data.subscriptions))
    return body


# ── Send Email API ──────────────────────────────────────


@app.post("/api/send")
def send_email_api(data: SendEmailRequest, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    if not s or not s.email_address or not s.encrypted_password:
        raise HTTPException(status_code=400, detail="请先在设置中配置邮箱凭据")

    body_md = data.body

    # Validate
    if data.email_type == "account" and not data.accounts:
        raise HTTPException(status_code=400, detail="请至少添加一条账号")
    if data.email_type == "subscription" and not data.subscriptions:
        raise HTTPException(status_code=400, detail="请至少添加一条订阅")

    # Convert markdown → HTML
    body_html = markdown.markdown(body_md, output_format="html")
    body_plain = body_md

    # Append signature HTML if selected
    if data.signature_id:
        sig = db.query(Signature).filter(Signature.id == data.signature_id).first()
        if sig and sig.content:
            body_html += "\n<hr>\n" + sig.content

    smtp_password = decrypt_password(s.encrypted_password)
    success, error_msg, msg_bytes = send_email(
        smtp_host=s.smtp_host,
        smtp_port=s.smtp_port,
        email_address=s.email_address,
        password=smtp_password,
        recipient=data.recipient,
        subject=data.subject,
        body_html=body_html,
        body_plain=body_plain,
        cc=data.cc,
    )

    archive_status = ""
    imap_host = s.imap_host or "partner.outlook.cn"
    imap_port = s.imap_port or 993
    if success and msg_bytes:
        archived, archive_err = save_to_sent_items(
            imap_host=imap_host,
            imap_port=imap_port,
            email_address=s.email_address,
            password=smtp_password,
            msg_bytes=msg_bytes,
        )
        archive_status = "archived" if archived else "failed"
        if not archived:
            logger.warning("IMAP archive failed: %s", archive_err)

    record = EmailHistory(
        email_type=data.email_type,
        recipient=data.recipient,
        cc=data.cc,
        subject=data.subject,
        body=body_md,
        status="success" if success else "failed",
        error_message=error_msg,
        archive_status=archive_status,
        template_id=data.template_id,
    )
    db.add(record)
    db.commit()

    if not success:
        raise HTTPException(status_code=500, detail=error_msg)

    return {"ok": True, "history_id": record.id, "archive_status": archive_status}


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
                archive_status=item.archive_status or "",
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
