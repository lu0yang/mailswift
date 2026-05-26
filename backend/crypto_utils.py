import os
import hashlib
import platform
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


SALT = b"mail-tool-fixed-salt-v1"


def _derive_key() -> bytes:
    """Derive a 256-bit key from machine-specific characteristics."""
    machine_id = f"{platform.node()}-{os.getlogin()}"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=600_000,
    )
    return kdf.derive(machine_id.encode())


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
    key = _derive_key()
    aesgcm = AESGCM(key)
    raw = base64.b64decode(encoded)
    nonce, ciphertext = raw[:12], raw[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
