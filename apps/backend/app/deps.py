from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import RoleEnum, User, UserSession
from .session_service import valid_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_tenant_id(request: Request) -> int:
    """Return the tenant_id resolved by TenantMiddleware.

    Falls back to 1 (the default tenant) when the middleware has not set the
    attribute, which can happen in tests that bypass the middleware stack.
    """
    return getattr(request.state, "tenant_id", 1)


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    tenant_id: int = Depends(get_tenant_id),
) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = int(payload.get("sub", 0))
        token_version = int(payload.get("ver", 0))
    except (JWTError, ValueError, TypeError) as exc:
        raise credentials_exception from exc
    user = db.get(User, user_id)
    if (
        not user or not user.active or (user.tenant_id or 1) != tenant_id
        or user.session_version != token_version
    ):
        raise credentials_exception
    session_id = payload.get("sid")
    if session_id:
        if not isinstance(session_id, str) or len(session_id) != 32:
            raise credentials_exception
        record = db.get(UserSession, session_id)
        if not valid_session(record, user, tenant_id):
            raise credentials_exception
    elif not settings.demo_mode:
        # Tokens issued before session tracking cannot be revoked per device.
        # Require fresh authentication outside demonstration environments.
        raise credentials_exception
    return user


def require_roles(*roles: RoleEnum):
    def _require(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Sem permissão")
        return current_user

    return _require
