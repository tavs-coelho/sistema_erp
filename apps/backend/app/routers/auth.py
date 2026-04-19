import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import settings
from ..db import get_db
from ..models import PasswordResetToken, User
from ..deps import get_current_user
from ..schemas import AuthMeResponse, LoginRequest, PasswordResetConfirm, PasswordResetRequest, RefreshRequest, TokenResponse
from ..security import create_access_token, create_refresh_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=AuthMeResponse)
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id, user.role.value),
        role=user.role,
        must_change_password=user.must_change_password,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        decoded = jwt.decode(payload.refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        if decoded.get("type") != "refresh":
            raise JWTError("invalid")
        user = db.get(User, int(decoded["sub"]))
    except (JWTError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Refresh token inválido") from exc
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id, user.role.value),
        role=user.role,
        must_change_password=user.must_change_password,
    )


@router.post("/logout")
def logout():
    return {"message": "Logout efetuado"}


@router.post("/request-password-reset")
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        return {"message": "Se usuário existir, o reset foi gerado"}
    token = secrets.token_urlsafe(24)
    reset = PasswordResetToken(user_id=user.id, token=token, expires_at=datetime.now(timezone.utc) + timedelta(minutes=30))
    db.add(reset)
    write_audit(db, user_id=user.id, action="create", entity="password_reset", entity_id=str(user.id), after_data={"token": token})
    db.commit()
    return {"message": "Reset gerado para demo", "reset_token": token}


@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    reset = db.query(PasswordResetToken).filter(PasswordResetToken.token == payload.token).first()
    if not reset or reset.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token inválido/expirado")
    user = db.get(User, reset.user_id)
    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = False
    db.delete(reset)
    write_audit(db, user_id=user.id, action="update", entity="users", entity_id=str(user.id), after_data={"password_reset": True})
    db.commit()
    return {"message": "Senha atualizada"}
