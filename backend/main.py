import logging
import re
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
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
    DEFAULT_PASSWORD_RESET_TEMPLATE,
)
from .crypto_utils import encrypt_password, decrypt_password
from .mail_sender import send_email, verify_connection

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

    # email_history table
    if "email_history" in insp.get_table_names():
        history_cols = {c["name"] for c in insp.get_columns("email_history")}
        if "template_id" not in history_cols:
            db.execute(sa.text("ALTER TABLE email_history ADD COLUMN template_id INTEGER"))

    # settings table — drop legacy smtp columns (cleanup after EWS migration)
    if "settings" in insp.get_table_names():
        settings_cols = {c["name"] for c in insp.get_columns("settings")}
        for col in ("smtp_host", "smtp_port"):
            if col in settings_cols:
                db.execute(sa.text(f"ALTER TABLE settings DROP COLUMN {col}"))

    db.commit()


def _migrate_templates(db: Session):
    """Create default email templates on first launch."""
    existing = db.query(EmailTemplate).count()
    if existing > 0:
        return

    s = db.query(Settings).first()
    account_content = DEFAULT_ACCOUNT_TEMPLATE
    sub_content = DEFAULT_SUBSCRIPTION_TEMPLATE
    pwd_reset_content = DEFAULT_PASSWORD_RESET_TEMPLATE
    if s:
        if s.account_template:
            account_content = s.account_template
            pwd_reset_content = s.account_template

    db.add(EmailTemplate(name="Create DevOps/DevOps NonRestricted", type="account", content=account_content))
    db.add(EmailTemplate(name="Password reset", type="account", content=pwd_reset_content))
    db.add(EmailTemplate(name="Request Subscription", type="subscription", content=sub_content))
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
    email_address: str = ""
    password: str = ""


class SettingsResponse(BaseModel):
    email_address: str
    password_masked: str
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
            email_address="",
            password_masked="",
            updated_at=None,
        )
    return SettingsResponse(
        email_address=s.email_address or "",
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
    if payload.password:
        s.encrypted_password = encrypt_password(payload.password)
    s.updated_at = datetime.now(timezone(timedelta(hours=8)))
    db.commit()
    return {"ok": True}


class TestConnectionRequest(BaseModel):
    email_address: str = ""
    password: str = ""


@app.post("/api/settings/test-connection")
def test_connection(data: TestConnectionRequest | None = None, db: Session = Depends(get_db)):
    s = db.query(Settings).first()

    # Use request body params if provided, otherwise fall back to saved settings
    if data and data.email_address and data.password:
        addr = data.email_address
        pwd = data.password
    elif s and s.email_address and s.encrypted_password:
        addr = s.email_address
        try:
            pwd = decrypt_password(s.encrypted_password)
        except ValueError:
            raise HTTPException(status_code=400, detail="密码解密失败，请重新配置凭据")
    else:
        raise HTTPException(status_code=400, detail="请先填写邮箱地址和密码")

    success, error_msg = verify_connection(addr, pwd)
    if not success:
        raise HTTPException(status_code=400, detail="连接失败")
    return {"ok": True}


# ── Image encoding (for pasted Outlook signatures) ─────

class EncodeImageRequest(BaseModel):
    url: str


@app.post("/api/encode-image")
def encode_image(data: EncodeImageRequest):
    from urllib.parse import urlparse, unquote
    from urllib.request import url2pathname
    import base64
    import mimetypes

    parsed = urlparse(data.url)
    if parsed.scheme not in ("file", ""):
        raise HTTPException(status_code=400, detail="Only file:// URLs are supported")

    filepath = url2pathname(parsed.path)

    # On Windows, path may have a leading slash (e.g. /C:/Users/...)
    if filepath and len(filepath) > 2 and filepath[0] == "/" and filepath[2] == ":":
        filepath = filepath[1:]

    if not Path(filepath).exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")

    try:
        with open(filepath, "rb") as f:
            img_data = f.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {e}")

    mime_type, _ = mimetypes.guess_type(filepath)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"

    b64 = base64.b64encode(img_data).decode("ascii")
    return {"data_uri": f"data:{mime_type};base64,{b64}"}


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
    """Substitute template variables into the body."""

    # Try new JSON format: {"header": "...", "item": "...", "footer": "..."}
    import json as _json
    try:
        tpl = _json.loads(template_content)
        if isinstance(tpl, dict) and "item" in tpl:
            return _render_new_format(tpl, data)
    except (_json.JSONDecodeError, TypeError):
        pass

    # Legacy / plain-text format: handle markers directly
    return _render_plain_markers(template_content, data)


def _render_new_format(tpl: dict, data: SendEmailRequest) -> str:
    """Render the new three-section JSON template format."""
    header = tpl.get("header", "")
    item_tpl = tpl.get("item", "")
    footer = tpl.get("footer", "")

    if data.email_type == "account":
        count = len(data.accounts)
        plural_val = "account" if count == 1 else "accounts"
        have_has = "has" if count == 1 else "have"
        header = header.replace("{account_plural}", plural_val)
        header = header.replace("{subscription_plural}", "subscription")
        header = header.replace("{have_has}", have_has)

        items = []
        for acct in data.accounts:
            part = item_tpl.replace("{username}", acct.account)
            part = part.replace("{password}", acct.password)
            part = part.replace("{account_type}", acct.account_type)
            items.append(part)
    else:
        count = len(data.subscriptions)
        plural_val = "subscription" if count == 1 else "subscriptions"
        have_has = "has" if count == 1 else "have"
        header = header.replace("{subscription_plural}", plural_val)
        header = header.replace("{account_plural}", "account")
        header = header.replace("{have_has}", have_has)

        items = []
        for sub in data.subscriptions:
            part = item_tpl.replace("{subscription_id}", sub.subscription_id)
            part = part.replace("{subscription_name}", sub.subscription_name)
            items.append(part)

    # Filter empty strings before joining to avoid double line breaks
    parts = [p for p in [header, *items, footer] if p.strip()]
    return "\n\n".join(parts)


def _render_plain_markers(text: str, data: SendEmailRequest) -> str:
    """Substitute new-format markers in non-JSON body text."""
    if data.email_type == "account":
        count = len(data.accounts)
        text = text.replace("{account_plural}", "account" if count == 1 else "accounts")
        text = text.replace("{have_has}", "has" if count == 1 else "have")
        text = text.replace("{account_list}", render_account_list(data.accounts))
        # Per-item markers: build a simple list for multi-account; single replacement for one
        if count == 1:
            a = data.accounts[0]
            text = text.replace("{username}", a.account)
            text = text.replace("{password}", a.password)
            text = text.replace("{account_type}", a.account_type)
        else:
            items = []
            for a in data.accounts:
                items.append(f"{a.account} / {a.password} / {a.account_type}")
            text = text.replace("{username}", "\n".join(items))
            text = text.replace("{password}", "\n".join(items))
            text = text.replace("{account_type}", "\n".join(items))
    else:
        count = len(data.subscriptions)
        text = text.replace("{subscription_plural}", "subscription" if count == 1 else "subscriptions")
        text = text.replace("{have_has}", "has" if count == 1 else "have")
        text = text.replace("{subscription_list}", render_subscription_list(data.subscriptions))
        if count == 1:
            s = data.subscriptions[0]
            text = text.replace("{subscription_id}", s.subscription_id)
            text = text.replace("{subscription_name}", s.subscription_name)
        else:
            items = []
            for s in data.subscriptions:
                items.append(f"{s.subscription_id} - {s.subscription_name}")
            text = text.replace("{subscription_id}", "\n".join(items))
            text = text.replace("{subscription_name}", "\n".join(items))
    return text


def _strip_markdown(md: str) -> str:
    """Strip common Markdown formatting for the plain-text email alternative."""
    import re
    # Remove link syntax: [text](url) → text
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)
    # Remove image syntax: ![alt](url) → alt
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove heading markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r"^[\s]*[-*+]\s+", "  ", text, flags=re.MULTILINE)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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

    # Server-side fallback: substitute any remaining {account_list}/{subscription_list}
    # placeholders in case the frontend didn't already do it.
    body_md = render_body(body_md, data)

    # Convert markdown → HTML
    body_html = markdown.markdown(body_md, output_format="html")

    # Plain text version: strip common markdown formatting for readability
    body_plain = _strip_markdown(body_md)

    # Append signature HTML if selected
    if data.signature_id:
        sig = db.query(Signature).filter(Signature.id == data.signature_id).first()
        if sig and sig.content:
            body_html += "\n<hr>\n" + sig.content

    try:
        smtp_password = decrypt_password(s.encrypted_password)
    except ValueError:
        raise HTTPException(status_code=400, detail="密码解密失败，请重新配置凭据")
    success, error_msg = send_email(
        email_address=s.email_address,
        password=smtp_password,
        recipient=data.recipient,
        subject=data.subject,
        body_html=body_html,
        body_plain=body_plain,
        cc=data.cc,
    )

    record = EmailHistory(
        email_type=data.email_type,
        recipient=data.recipient,
        cc=data.cc,
        subject=data.subject,
        body=body_md,
        status="success" if success else "failed",
        error_message=error_msg,
        template_id=data.template_id,
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


@app.post("/api/reset")
def reset_app(db: Session = Depends(get_db)):
    """Reset the application to factory defaults: clear credentials,
    delete all templates/signatures/history, and re-create default templates."""
    # Clear credentials
    s = db.query(Settings).first()
    if s:
        s.encrypted_password = ""
        s.email_address = ""
        db.flush()

    # Delete all user data
    db.query(EmailHistory).delete()
    db.query(Signature).delete()
    db.query(EmailTemplate).delete()
    db.flush()

    # Re-create default templates
    _migrate_templates(db)

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
