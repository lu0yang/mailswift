import os
import base64
import logging
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


SALT = b"mail-tool-fixed-salt-v1"
MACHINE_ID_FILE = Path(__file__).resolve().parent / ".machine_id"
logger = logging.getLogger(__name__)


_mid_cache: str | None = None


def _machine_id() -> str:
    """Return a stable machine identifier, creating one on first run."""
    global _mid_cache

    if _mid_cache is not None:
        return _mid_cache

    if MACHINE_ID_FILE.exists():
        try:
            _mid_cache = MACHINE_ID_FILE.read_text().strip()
            return _mid_cache
        except OSError:
            pass

    _mid_cache = uuid4().hex
    try:
        MACHINE_ID_FILE.write_text(_mid_cache)
    except OSError:
        logger.warning(
            "Cannot persist machine-id to %s; passwords will be lost on next restart",
            MACHINE_ID_FILE,
        )
    return _mid_cache


def _derive_key() -> bytes:
    """Derive a 256-bit key from a stable machine identifier."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=600_000,
    )
    return kdf.derive(_machine_id().encode())


def encrypt_password(plaintext: str) -> str:
    """Encrypt a password string and return base64-encoded ciphertext."""
    if not plaintext:
        return ""
    key = _derive_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_password(encoded: str) -> str:
    """Decrypt a base64-encoded ciphertext back to the original password."""
    if not encoded:
        return ""
    try:
        key = _derive_key()
        aesgcm = AESGCM(key)
        raw = base64.b64decode(encoded)
        nonce, ciphertext = raw[:12], raw[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode()
    except Exception:
        # Decryption failed — this can happen if the machine-id file was
        # deleted or the DB was copied from another machine.  Return the
        # raw ciphertext as a hint so the caller can show a clear message.
        raise ValueError(
            "无法解密密码：密钥与加密时不一致。"
            "如果这是从另一台机器复制的数据库，请重新配置 SMTP 凭据。"
        )
