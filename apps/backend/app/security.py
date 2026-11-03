from datetime import datetime, timedelta, timezone
import bcrypt
import secrets
from jose import jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Prefixos $2a$/$2b$/$2y$ identificam hashes bcrypt legados.
    if hashed_password.startswith("$2"):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except ValueError:
            return False
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_token(data: dict, minutes: int) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(
    user_id: int, role: str, version: int = 0, session_id: str | None = None
) -> str:
    claims = {"sub": str(user_id), "role": role, "type": "access", "ver": version}
    if session_id:
        claims["sid"] = session_id
    return create_token(claims, settings.access_token_minutes)


def create_refresh_token(
    user_id: int, role: str, version: int = 0,
    session_id: str | None = None, jti: str | None = None,
) -> str:
    claims = {"sub": str(user_id), "role": role, "type": "refresh", "ver": version}
    if session_id:
        claims["sid"] = session_id
        claims["jti"] = jti or secrets.token_urlsafe(24)
    return create_token(claims, settings.refresh_token_minutes)


def create_mfa_challenge(user_id: int, tenant_id: int, version: int, nonce: str) -> str:
    return create_token({
        "sub": str(user_id), "tenant": tenant_id, "type": "mfa_challenge",
        "ver": version, "jti": nonce,
    }, 3)
