"""Per-device session lifecycle.

The signed JWT is a bearer credential; its plaintext is never stored.
Row locking serializes competing refresh requests in PostgreSQL.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import Request
from sqlalchemy.orm import Session

from .config import settings
from .models import User, UserSession
from .schemas import TokenResponse
from .security import create_access_token, create_refresh_token


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime) -> datetime:
    """SQLite stores timezone-naive datetimes. Interpret those as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def valid_session(record: UserSession | None, user: User, tenant_id: int) -> bool:
    return bool(
        record and record.user_id == user.id and record.tenant_id == tenant_id
        and record.session_version == user.session_version
        and record.revoked_at is None and aware(record.expires_at) > utc_now()
    )


def _refresh_token(user: User, sid: str) -> str:
    # Random JWT ID ensures rotation issues a distinct bearer credential even
    # when consecutive refreshes occur within the same second.
    return create_refresh_token(
        user.id, user.role.value, user.session_version,
        session_id=sid, jti=secrets.token_urlsafe(24),
    )


def create_device_session(db: Session, user: User, tenant_id: int, request: Request) -> TokenResponse:
    sid = secrets.token_hex(16)
    token = _refresh_token(user, sid)
    now = utc_now()
    db.add(UserSession(
        id=sid, user_id=user.id, tenant_id=tenant_id, session_version=user.session_version,
        refresh_token_hash=refresh_hash(token),
        user_agent=(request.headers.get("user-agent") or "")[:200],
        created_at=now, last_used_at=now,
        expires_at=now + timedelta(minutes=settings.refresh_token_minutes),
    ))
    db.commit()
    return TokenResponse(
        access_token=create_access_token(
            user.id, user.role.value, user.session_version, session_id=sid,
        ),
        refresh_token=token, role=user.role,
        must_change_password=user.must_change_password,
    )


def rotate_refresh_token(
    db: Session, user: User, tenant_id: int, session_id: str, presented_token: str
) -> TokenResponse | None:
    record = (
        db.query(UserSession)
        .filter(UserSession.id == session_id, UserSession.user_id == user.id,
                UserSession.tenant_id == tenant_id)
        .with_for_update().populate_existing().first()
    )
    if not valid_session(record, user, tenant_id):
        return None
    if not hmac.compare_digest(record.refresh_token_hash, refresh_hash(presented_token)):
        # Any attempted replay revokes this one device's session, including
        # its access tokens. Other devices stay connected.
        record.revoked_at = utc_now()
        db.commit()
        return None
    new_token = _refresh_token(user, session_id)
    now = utc_now()
    record.refresh_token_hash = refresh_hash(new_token)
    record.last_used_at = now
    record.expires_at = now + timedelta(minutes=settings.refresh_token_minutes)
    db.commit()
    return TokenResponse(
        access_token=create_access_token(
            user.id, user.role.value, user.session_version, session_id=session_id,
        ),
        refresh_token=new_token, role=user.role,
        must_change_password=user.must_change_password,
    )


def revoke_user_sessions(db: Session, user_id: int) -> None:
    """Mark every device session revoked within the caller's transaction."""
    db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked_at.is_(None),
    ).update({"revoked_at": utc_now()}, synchronize_session=False)
