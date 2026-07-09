"""Security utilities for the RAG platform."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import re
import secrets
import threading
import time
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

log = logging.getLogger(__name__)

_fernet: Fernet | None = None
_fernet_lock = threading.Lock()


def _get_fernet(master_key: str | None = None) -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet
    with _fernet_lock:
        if _fernet is not None:
            return _fernet
        key = master_key or os.getenv("RAG_ENCRYPTION_KEY", "")
        if not key:
            raise RuntimeError(
                "RAG_ENCRYPTION_KEY is not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        key_bytes = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        _fernet = Fernet(key_bytes)
    return _fernet


def encrypt_api_key(plaintext: str, master_key: str | None = None) -> str:
    if not plaintext:
        return ""
    f = _get_fernet(master_key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str, master_key: str | None = None) -> str:
    if not ciphertext:
        return ""
    f = _get_fernet(master_key)
    return f.decrypt(ciphertext.encode()).decode()


def generate_api_key(tenant_id: str) -> tuple[str, str]:
    suffix = secrets.token_urlsafe(24)
    raw_key = f"rbs_rag_sk_{tenant_id}_{suffix}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def validate_api_key(raw_key: str, key_hash: str) -> bool:
    computed = hashlib.sha256(raw_key.encode()).hexdigest()
    return hmac.compare_digest(computed, key_hash)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|above|all)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are\s+now", re.IGNORECASE),
    re.compile(r"forget\s+(?:all\s+)?(?:your\s+)?(?:previous|everything|instructions)", re.IGNORECASE),
    re.compile(r"new\s+(prompt|instruction|task|rules)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if|though)", re.IGNORECASE),
    re.compile(r"pretend\s+(to\s+be|that|you)", re.IGNORECASE),
    re.compile(r"role[- ]?play\s+as", re.IGNORECASE),
    re.compile(r"you\s+(are|will)\s+now\s+(act|behave|respond)", re.IGNORECASE),
    re.compile(rf"{re.escape(chr(10))}{{2,}}.*(system|assistant|user)\s*:", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> list[str]:
    detected = []
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            detected.append(match.group())
    return detected


def generate_jwt(tenant_id: str, secret: str, expiry_hours: int = 24) -> str:
    import jwt as pyjwt
    payload = {
        "tenant_id": tenant_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + expiry_hours * 3600,
        "jti": secrets.token_hex(16),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def verify_jwt(token: str, secret: str) -> dict[str, Any] | None:
    import jwt as pyjwt
    try:
        return pyjwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None
