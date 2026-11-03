"""RFC 6238 TOTP plus encrypted secrets and single-use recovery codes."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .models import MfaRecoveryCode, User, UserMfa


def _cipher() -> Fernet:
    key = settings.mfa_encryption_key
    if not key:
        raise HTTPException(status_code=503, detail="MFA indisponível: chave de criptografia não configurada")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="MFA indisponível: configuração inválida") from exc


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def encrypt_secret(secret: str) -> str:
    return _cipher().encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_secret(value: str) -> str:
    try:
        return _cipher().decrypt(value.encode("ascii")).decode("ascii")
    except (InvalidToken, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Segredo MFA não pode ser recuperado") from exc


def provisioning_uri(secret: str, username: str) -> str:
    issuer = "ERP Gestao Publica"
    label = quote(f"{issuer}:{username}", safe="")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer, safe='')}&digits=6&period=30"


def totp_at(secret: str, counter: int) -> str:
    padded = secret + "=" * (-len(secret) % 8)
    key = base64.b32decode(padded, casefold=False)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 1000000:06d}"


def valid_totp_counter(
    secret: str, code: str, last_used: int = -1, now: float | None = None
) -> int | None:
    if len(code) != 6 or not code.isascii() or not code.isdecimal():
        return None
    current = int((time.time() if now is None else now) // 30)
    for counter in (current - 1, current, current + 1):
        if counter >= 0 and counter > last_used and hmac.compare_digest(totp_at(secret, counter), code):
            return counter
    return None


def consume_mfa_code(db: Session, user: User, code: str) -> bool:
    record = db.get(UserMfa, user.id)
    if not record or not record.enabled or not record.encrypted_secret:
        return False
    secret = decrypt_secret(record.encrypted_secret)
    counter = valid_totp_counter(secret, code, record.last_used_counter)
    if counter is not None:
        record.last_used_counter = counter
        return True
    if len(code) != 32 or any(ch not in "0123456789abcdef" for ch in code):
        return False
    hashed = hashlib.sha256(code.encode("ascii")).hexdigest()
    recovered = db.query(MfaRecoveryCode).filter(
        MfaRecoveryCode.user_id == user.id, MfaRecoveryCode.code_hash == hashed
    ).first()
    if recovered is not None:
        db.delete(recovered)
        return True
    return False


def replace_recovery_codes(db: Session, user_id: int) -> list[str]:
    db.query(MfaRecoveryCode).filter(MfaRecoveryCode.user_id == user_id).delete()
    codes = [secrets.token_hex(16) for _ in range(10)]
    for code in codes:
        db.add(MfaRecoveryCode(user_id=user_id, code_hash=hashlib.sha256(code.encode("ascii")).hexdigest()))
    return codes
