import logging
import re
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import init_db, get_db
from .models import (
    Settings, EmailHistory, EmailTemplate, Signature, IncidentStore,
    DEFAULT_ACCOUNT_TEMPLATE, DEFAULT_SUBSCRIPTION_TEMPLATE,
    DEFAULT_PASSWORD_RESET_TEMPLATE,
    DEFAULT_HP_INITIAL_TEMPLATE,
    DEFAULT_HP_UPDATED_TEMPLATE,
    DEFAULT_HP_MITIGATED_TEMPLATE,
)
from .crypto_utils import encrypt_password, decrypt_password
from .mail_sender import send_email, verify_connection

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
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

    # settings table — add account-switching columns
    if "settings" in insp.get_table_names():
        settings_cols = {c["name"] for c in insp.get_columns("settings")}
        if "label" not in settings_cols:
            db.execute(sa.text("ALTER TABLE settings ADD COLUMN label VARCHAR(100) DEFAULT ''"))
        if "is_active" not in settings_cols:
            db.execute(sa.text("ALTER TABLE settings ADD COLUMN is_active BOOLEAN DEFAULT 0"))
            # First-time migration: mark the existing account as active
            db.execute(sa.text("UPDATE settings SET is_active = 1 WHERE email_address != '' AND is_active = 0"))

    # settings table — drop legacy smtp columns (cleanup after EWS migration)
    if "settings" in insp.get_table_names():
        settings_cols = {c["name"] for c in insp.get_columns("settings")}
        for col in ("smtp_host", "smtp_port", "imap_host", "imap_port",
                     "account_template", "subscription_template"):
            if col in settings_cols:
                try:
                    db.execute(sa.text(f"ALTER TABLE settings DROP COLUMN {col}"))
                except Exception:
                    pass  # SQLite < 3.35 doesn't support DROP COLUMN; harmless

    db.commit()


def _migrate_templates(db: Session):
    """Create default email templates on first launch."""
    existing = db.query(EmailTemplate).count()
    if existing == 0:
        db.add(EmailTemplate(name="Create DevOps/DevOps NonRestricted", type="account", content=DEFAULT_ACCOUNT_TEMPLATE))
        db.add(EmailTemplate(name="Password reset", type="account", content=DEFAULT_PASSWORD_RESET_TEMPLATE))
        db.add(EmailTemplate(name="Request Subscription", type="subscription", content=DEFAULT_SUBSCRIPTION_TEMPLATE))
        db.add(EmailTemplate(name="HP INITIAL", type="high_priority", content=DEFAULT_HP_INITIAL_TEMPLATE))
        db.add(EmailTemplate(name="HP UPDATED", type="high_priority", content=DEFAULT_HP_UPDATED_TEMPLATE))
        db.add(EmailTemplate(name="HP MITIGATED", type="high_priority", content=DEFAULT_HP_MITIGATED_TEMPLATE))
        db.commit()
        logger.info("Created default email templates")
        return

    # Backfill HP INITIAL for existing databases
    hp = db.query(EmailTemplate).filter(EmailTemplate.name == "HP INITIAL").first()
    if not hp:
        db.add(EmailTemplate(name="HP INITIAL", type="high_priority", content=DEFAULT_HP_INITIAL_TEMPLATE))
        db.commit()
        logger.info("Backfilled HP INITIAL template")

    # Backfill HP UPDATED for existing databases
    hp_upd = db.query(EmailTemplate).filter(EmailTemplate.name == "HP UPDATED").first()
    if not hp_upd:
        db.add(EmailTemplate(name="HP UPDATED", type="high_priority", content=DEFAULT_HP_UPDATED_TEMPLATE))
        db.commit()
        logger.info("Backfilled HP UPDATED template")

    # Backfill HP MITIGATED for existing databases
    hp_mit = db.query(EmailTemplate).filter(EmailTemplate.name == "HP MITIGATED").first()
    if not hp_mit:
        db.add(EmailTemplate(name="HP MITIGATED", type="high_priority", content=DEFAULT_HP_MITIGATED_TEMPLATE))
        db.commit()
        logger.info("Backfilled HP MITIGATED template")


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
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic schemas ────────────────────────────────────


class SettingsUpdate(BaseModel):
    email_address: str = ""
    password: str = ""
    label: str = ""


class SettingsResponse(BaseModel):
    id: int
    email_address: str
    password_masked: str
    label: str
    updated_at: str | None


class AccountListItem(BaseModel):
    id: int
    email_address: str
    label: str
    is_active: bool


class AccountItem(BaseModel):
    account: str
    password: str
    account_type: str


class SubscriptionItem(BaseModel):
    subscription_id: str
    subscription_name: str


class AttachmentItem(BaseModel):
    filename: str
    content_base64: str


class SendEmailRequest(BaseModel):
    email_type: str = Field(..., pattern="^(account|subscription|high_priority)$")
    recipient: str
    cc: str = ""
    subject: str = ""
    body: str = ""
    template_id: int | None = None
    signature_id: int | None = None
    accounts: list[AccountItem] = []
    subscriptions: list[SubscriptionItem] = []
    attachments: list[AttachmentItem] = []
    ticket_id: str = ""
    form_data: dict | None = None


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
    type: str = Field(..., pattern="^(account|subscription|high_priority)$")
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


def _get_active_settings(db: Session) -> Settings | None:
    return db.query(Settings).filter(Settings.is_active == True).first()


@app.get("/api/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    s = _get_active_settings(db)
    if not s:
        return SettingsResponse(
            id=0, email_address="", password_masked="", label="", updated_at=None,
        )
    return SettingsResponse(
        id=s.id,
        email_address=s.email_address or "",
        password_masked="********" if s.encrypted_password else "",
        label=s.label or "",
        updated_at=s.updated_at.isoformat() if s.updated_at else None,
    )


@app.post("/api/settings")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    # Find existing account with same email, or create a new one
    s = db.query(Settings).filter(Settings.email_address == payload.email_address).first()
    if not s:
        s = Settings()
        db.add(s)
        s.is_active = False  # will be set to True below
    s.email_address = payload.email_address
    if payload.password:
        s.encrypted_password = encrypt_password(payload.password)
    s.label = payload.label or payload.email_address
    s.updated_at = datetime.now(timezone(timedelta(hours=8)))
    # Make this the active account
    db.query(Settings).filter(Settings.is_active == True).update(
        {"is_active": False}, synchronize_session=False
    )
    s.is_active = True
    db.commit()
    return {"ok": True, "id": s.id}


class TestConnectionRequest(BaseModel):
    email_address: str = ""
    password: str = ""


@app.post("/api/settings/test-connection")
def test_connection(data: TestConnectionRequest | None = None, db: Session = Depends(get_db)):
    s = _get_active_settings(db)

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

    # Block path traversal attacks
    if ".." in filepath.replace("\\", "/").split("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    # On Windows, path may have a leading slash (e.g. /C:/Users/...)
    if filepath and len(filepath) > 2 and filepath[0] == "/" and filepath[2] == ":":
        filepath = filepath[1:]

    if not Path(filepath).exists():
        raise HTTPException(status_code=404, detail="File not found")

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
        db.query(Signature).filter(Signature.is_default == True).update(  # noqa: E712
            {"is_default": False}, synchronize_session=False
        )
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
        db.query(Signature).filter(Signature.is_default == True).update(  # noqa: E712
            {"is_default": False}, synchronize_session=False
        )
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


def _strip_html(html: str) -> str:
    """Strip HTML tags for the plain-text email alternative."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _upsert_incident(db: Session, ticket_id: str, form_data: dict | None):
    """Insert or update an incident record in incident_store."""
    import json
    incident = db.query(IncidentStore).filter(IncidentStore.ticket_id == ticket_id).first()
    if incident:
        incident.form_data = json.dumps(form_data or {}, ensure_ascii=False)
        incident.updated_at = datetime.now(timezone(timedelta(hours=8)))
        # Update status from form_data if present
        if form_data and "status_prefix" in form_data:
            incident.status = form_data["status_prefix"]
    else:
        incident = IncidentStore(
            ticket_id=ticket_id,
            status=form_data.get("status_prefix", "INITIAL") if form_data else "INITIAL",
            form_data=json.dumps(form_data or {}, ensure_ascii=False),
        )
        db.add(incident)
    db.commit()


# ── Send Email API ──────────────────────────────────────


@app.post("/api/send")
def send_email_api(data: SendEmailRequest, db: Session = Depends(get_db)):
    s = _get_active_settings(db)
    if not s or not s.email_address or not s.encrypted_password:
        raise HTTPException(status_code=400, detail="请先在设置中配置邮箱凭据")

    body_html = data.body

    # Validate
    if data.email_type == "account" and not data.accounts:
        raise HTTPException(status_code=400, detail="请至少添加一条账号")
    if data.email_type == "subscription" and not data.subscriptions:
        raise HTTPException(status_code=400, detail="请至少添加一条订阅")

    # Plain text version: strip HTML tags
    body_plain = _strip_html(body_html)

    # Append signature HTML if selected
    if data.signature_id:
        sig = db.query(Signature).filter(Signature.id == data.signature_id).first()
        if sig and sig.content:
            if "sig-paste-wrap" in sig.content:
                body_html += "\n<br>\n" + sig.content
            else:
                body_html += "\n<br>\n<div style=\"max-width:600px;\">" + sig.content + "</div>"

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
        attachments=[a.model_dump() for a in data.attachments] if data.attachments else [],
    )

    record = EmailHistory(
        email_type=data.email_type,
        recipient=data.recipient,
        cc=data.cc,
        subject=data.subject,
        body=body_html,
        status="success" if success else "failed",
        error_message=error_msg,
        template_id=data.template_id,
    )
    db.add(record)
    db.commit()

    if not success:
        raise HTTPException(status_code=500, detail=error_msg)

    # Upsert incident_store for HP emails
    if data.email_type == "high_priority" and data.ticket_id:
        _upsert_incident(db, data.ticket_id, data.form_data)

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
    """Reset the application to factory defaults: clear credentials from the
    active account, delete all templates/signatures/history, and re-create
    default templates."""
    # Clear active account credentials
    s = _get_active_settings(db)
    if s:
        s.encrypted_password = ""
        s.email_address = ""
        s.label = ""
        s.updated_at = datetime.now(timezone(timedelta(hours=8)))
        db.flush()

    # Delete all user data
    db.query(EmailHistory).delete()
    db.query(Signature).delete()
    db.query(EmailTemplate).delete()
    db.flush()

    # Re-create default templates
    _migrate_templates(db)

    return {"ok": True}


# ── Account management ──────────────────────────────────


@app.get("/api/accounts", response_model=list[AccountListItem])
def list_accounts(db: Session = Depends(get_db)):
    items = db.query(Settings).filter(Settings.email_address != "").order_by(Settings.updated_at.desc()).all()
    return [
        AccountListItem(
            id=a.id,
            email_address=a.email_address or "",
            label=a.label or a.email_address or "",
            is_active=a.is_active,
        )
        for a in items
    ]


@app.post("/api/accounts/{account_id}/switch")
def switch_account(account_id: int, db: Session = Depends(get_db)):
    a = db.query(Settings).filter(Settings.id == account_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="账户不存在")
    db.query(Settings).filter(Settings.is_active == True).update(
        {"is_active": False}, synchronize_session=False
    )
    a.is_active = True
    db.commit()
    return {"ok": True}


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    a = db.query(Settings).filter(Settings.id == account_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="账户不存在")
    db.delete(a)
    db.commit()
    return {"ok": True}


# ── Incident Store APIs ─────────────────────────────────


@app.get("/api/incident-store/lookup")
def lookup_incident(ticket_id: str = Query(...), db: Session = Depends(get_db)):
    """Look up a previous incident by ticket_id."""
    incident = db.query(IncidentStore).filter(IncidentStore.ticket_id == ticket_id).first()
    if not incident:
        return {"ok": False, "detail": f"未找到关联事件 [{ticket_id}]，请手动填写表单信息"}
    try:
        import json
        form_data = json.loads(incident.form_data)
    except Exception:
        form_data = {}
    return {"ok": True, "data": {"status": incident.status, "form_data": form_data}}


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
