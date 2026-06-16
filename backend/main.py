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
    EmailHistory, EmailTemplate, Signature, IncidentStore, User,
    DEFAULT_ACCOUNT_TEMPLATE, DEFAULT_SUBSCRIPTION_TEMPLATE,
    DEFAULT_PASSWORD_RESET_TEMPLATE,
    DEFAULT_HP_INITIAL_TEMPLATE,
    DEFAULT_HP_UPDATED_TEMPLATE,
    DEFAULT_HP_MITIGATED_TEMPLATE,
)
from .auth import get_current_user, login_or_register
from .mail_sender import send_email

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

    # email_history: add template_id (legacy)
    if "msw_history" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("msw_history")}
        if "template_id" not in cols:
            db.execute(sa.text("ALTER TABLE msw_history ADD COLUMN template_id INTEGER"))
        if "sender" not in cols:
            db.execute(sa.text("ALTER TABLE msw_history ADD COLUMN sender VARCHAR(255) DEFAULT ''"))

    # email_templates: add user_id (legacy)
    if "msw_templates" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("msw_templates")}
        if "user_id" not in cols:
            db.execute(sa.text("ALTER TABLE msw_templates ADD COLUMN user_id INTEGER"))

    # signatures: add user_id (legacy)
    if "msw_signatures" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("msw_signatures")}
        if "user_id" not in cols:
            db.execute(sa.text("ALTER TABLE msw_signatures ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0"))

    # incident_store: add created_by / updated_by (legacy)
    if "msw_incident" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("msw_incident")}
        if "created_by" not in cols:
            db.execute(sa.text("ALTER TABLE msw_incident ADD COLUMN created_by INTEGER"))
        if "updated_by" not in cols:
            db.execute(sa.text("ALTER TABLE msw_incident ADD COLUMN updated_by INTEGER"))

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


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str
    display_name: str


class MeResponse(BaseModel):
    id: int
    email: str
    display_name: str


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
    ews_password: str = ""
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
    sender: str
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
    is_public: bool


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


# ── Auth APIs ───────────────────────────────────────────


@app.post("/api/auth/login", response_model=AuthResponse)
def api_login(data: LoginRequest, db: Session = Depends(get_db)):
    token = login_or_register(db, data.email, data.password)
    if not token:
        raise HTTPException(status_code=401, detail="邮箱或密码错误，请检查后重试")
    user = db.query(User).filter(User.email == data.email).first()
    return AuthResponse(token=token, email=user.email, display_name=user.display_name or "")


@app.get("/api/auth/me", response_model=MeResponse)
def api_me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email, display_name=user.display_name or "")


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
    user: User = Depends(get_current_user),
):
    # 返回公共模板（user_id IS NULL）+ 当前用户的自定义模板
    q = db.query(EmailTemplate).filter(
        (EmailTemplate.user_id.is_(None)) | (EmailTemplate.user_id == user.id)
    )
    if type:
        q = q.filter(EmailTemplate.type == type)
    items = q.order_by(EmailTemplate.created_at.desc()).all()
    return [
        TemplateResponse(
            id=t.id, name=t.name, type=t.type, content=t.content,
            created_at=t.created_at.isoformat() if t.created_at else "",
            is_public=t.user_id is None,
        )
        for t in items
    ]


@app.post("/api/templates", response_model=TemplateResponse)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 用户仅允许创建 account / subscription 类型的模板
    if data.type not in ("account", "subscription"):
        raise HTTPException(status_code=400, detail="仅允许创建 account 或 subscription 类型的模板")
    t = EmailTemplate(user_id=user.id, name=data.name, type=data.type, content=data.content)
    db.add(t)
    db.commit()
    db.refresh(t)
    return TemplateResponse(
        id=t.id, name=t.name, type=t.type, content=t.content,
        created_at=t.created_at.isoformat() if t.created_at else "",
        is_public=t.user_id is None,
    )


@app.put("/api/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    # 公共模板禁止修改
    if t.user_id is None:
        raise HTTPException(status_code=403, detail="系统默认模板不可修改")
    # 非所有者不可修改
    if t.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权修改此模板")
    t.name = data.name
    t.content = data.content
    db.commit()
    db.refresh(t)
    return TemplateResponse(
        id=t.id, name=t.name, type=t.type, content=t.content,
        created_at=t.created_at.isoformat() if t.created_at else "",
        is_public=t.user_id is None,
    )


@app.delete("/api/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    # 公共模板禁止删除
    if t.user_id is None:
        raise HTTPException(status_code=403, detail="系统默认模板不可删除")
    # 非所有者不可删除
    if t.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权删除此模板")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ── Signature CRUD ──────────────────────────────────────


@app.get("/api/signatures", response_model=list[SignatureResponse])
def list_signatures(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = db.query(Signature).filter(
        Signature.user_id == user.id
    ).order_by(Signature.created_at.desc()).all()
    return [
        SignatureResponse(
            id=s.id, name=s.name, content=s.content,
            is_default=s.is_default,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in items
    ]


@app.post("/api/signatures", response_model=SignatureResponse)
def create_signature(
    data: SignatureCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.is_default:
        db.query(Signature).filter(
            Signature.user_id == user.id,
            Signature.is_default.is_(True),
        ).update({"is_default": False}, synchronize_session=False)
    s = Signature(user_id=user.id, name=data.name, content=data.content, is_default=data.is_default)
    db.add(s)
    db.commit()
    db.refresh(s)
    return SignatureResponse(
        id=s.id, name=s.name, content=s.content,
        is_default=s.is_default,
        created_at=s.created_at.isoformat() if s.created_at else "",
    )


@app.put("/api/signatures/{signature_id}", response_model=SignatureResponse)
def update_signature(
    signature_id: int,
    data: SignatureUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = db.query(Signature).filter(
        Signature.id == signature_id,
        Signature.user_id == user.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="签名不存在")
    if data.is_default:
        db.query(Signature).filter(
            Signature.user_id == user.id,
            Signature.is_default.is_(True),
        ).update({"is_default": False}, synchronize_session=False)
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
def delete_signature(
    signature_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = db.query(Signature).filter(
        Signature.id == signature_id,
        Signature.user_id == user.id,
    ).first()
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


def _upsert_incident(db: Session, ticket_id: str, form_data: dict | None, user: User):
    """Insert or update an incident record in incident_store."""
    import json
    incident = db.query(IncidentStore).filter(IncidentStore.ticket_id == ticket_id).first()
    if incident:
        incident.form_data = json.dumps(form_data or {}, ensure_ascii=False)
        incident.updated_at = datetime.now(timezone(timedelta(hours=8)))
        incident.updated_by = user.id
        if form_data and "status_prefix" in form_data:
            incident.status = form_data["status_prefix"]
    else:
        incident = IncidentStore(
            ticket_id=ticket_id,
            status=form_data.get("status_prefix", "INITIAL") if form_data else "INITIAL",
            form_data=json.dumps(form_data or {}, ensure_ascii=False),
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(incident)
    db.commit()


# ── Send Email API ──────────────────────────────────────


@app.post("/api/send")
def send_email_api(
    data: SendEmailRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not data.ews_password:
        raise HTTPException(status_code=400, detail="密码不能为空")

    body_html = data.body

    if data.email_type == "account" and not data.accounts:
        raise HTTPException(status_code=400, detail="请至少添加一条账号")
    if data.email_type == "subscription" and not data.subscriptions:
        raise HTTPException(status_code=400, detail="请至少添加一条订阅")

    body_plain = _strip_html(body_html)

    if data.signature_id:
        sig = db.query(Signature).filter(Signature.id == data.signature_id).first()
        if sig and sig.content:
            if "sig-paste-wrap" in sig.content:
                body_html += "\n<br>\n" + sig.content
            else:
                body_html += "\n<br>\n<div style=\"max-width:600px;\">" + sig.content + "</div>"

    success, error_msg = send_email(
        email_address=user.email,
        password=data.ews_password,
        recipient=data.recipient,
        subject=data.subject,
        body_html=body_html,
        body_plain=body_plain,
        cc=data.cc,
        attachments=[a.model_dump() for a in data.attachments] if data.attachments else [],
    )

    record = EmailHistory(
        sender=user.email,
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

    if data.email_type == "high_priority" and data.ticket_id:
        _upsert_incident(db, data.ticket_id, data.form_data, user)

    return {"ok": True, "history_id": record.id}


# ── History APIs ───────────────────────────────────────


@app.get("/api/history", response_model=HistoryListResponse)
def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    email_type: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(EmailHistory).filter(EmailHistory.sender == user.email)
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
                sender=item.sender or "",
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
def delete_history(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = db.query(EmailHistory).filter(
        EmailHistory.id == record_id,
        EmailHistory.sender == user.email,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}


@app.post("/api/reset")
def reset_app(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete all personal data for the current user (templates, signatures, history)."""
    db.query(EmailHistory).filter(EmailHistory.sender == user.email).delete()
    db.query(Signature).filter(Signature.user_id == user.id).delete()
    db.query(EmailTemplate).filter(
        EmailTemplate.user_id == user.id
    ).delete(synchronize_session=False)
    db.flush()

    _migrate_templates(db)

    return {"ok": True}


# ── Incident Store APIs ─────────────────────────────────


@app.get("/api/incident-store/lookup")
def lookup_incident(
    ticket_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Look up a previous incident by ticket_id, update last editor."""
    incident = db.query(IncidentStore).filter(IncidentStore.ticket_id == ticket_id).first()
    if not incident:
        return {"ok": False, "detail": f"未找到关联事件 [{ticket_id}]，请手动填写表单信息"}
    # Record who accessed this incident (last viewer)
    incident.updated_by = user.id
    db.commit()
    try:
        import json
        form_data = json.loads(incident.form_data)
    except Exception:
        form_data = {}
    return {"ok": True, "data": {"status": incident.status, "form_data": form_data}}


# ── Domain presets ─────────────────────────────────────


@app.get("/api/domains")
def get_domains(user: User = Depends(get_current_user)):
    import json
    try:
        return {"domains": json.loads(user.domains or "[]")}
    except Exception:
        return {"domains": []}


class DomainsUpdate(BaseModel):
    domains: list[str]


@app.post("/api/domains")
def update_domains(data: DomainsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    import json
    user.domains = json.dumps(data.domains, ensure_ascii=False)
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
