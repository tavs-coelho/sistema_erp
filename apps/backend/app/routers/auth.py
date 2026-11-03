"""Authentication with tenant-bound JWTs, opt-in TOTP MFA and session revocation."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import settings
from ..db import get_db
from ..deps import get_current_user, get_tenant_id
from ..limiter import limiter as _limiter
from ..mfa import (
    consume_mfa_code, decrypt_secret, encrypt_secret, generate_totp_secret,
    provisioning_uri, replace_recovery_codes, valid_totp_counter,
)
from ..models import MfaRecoveryCode, PasswordResetToken, User, UserMfa
from ..schemas import (
    AuthMeResponse, LoginRequest, MfaChallengeResponse, MfaCodeRequest,
    MfaConfirmResponse, MfaDisableRequest, MfaLoginConfirm, MfaSetupRequest,
    MfaSetupResponse, MfaStatusResponse, PasswordResetConfirm,
    PasswordResetRequest, RefreshRequest, TokenResponse,
)
from ..security import (
    create_access_token, create_mfa_challenge, create_refresh_token,
    hash_password, verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value, user.session_version),
        refresh_token=create_refresh_token(user.id, user.role.value, user.session_version),
        role=user.role,
        must_change_password=user.must_change_password,
    )


def _find_user(db: Session, username: str, tenant_id: int) -> User | None:
    query = db.query(User).filter(User.username == username)
    if tenant_id == 1:
        query = query.filter((User.tenant_id == 1) | (User.tenant_id.is_(None)))
    else:
        query = query.filter(User.tenant_id == tenant_id)
    return query.first()


def _active_tenant_user(db: Session, user_id: int, tenant_id: int) -> User | None:
    user = db.get(User, user_id)
    if not user or not user.active or (user.tenant_id or 1) != tenant_id:
        return None
    return user


def _bad_mfa() -> HTTPException:
    return HTTPException(status_code=401, detail="Código ou desafio MFA inválido")


@router.get("/me", response_model=AuthMeResponse)
def me(current_user: User = Depends(get_current_user)):
    return AuthMeResponse.model_validate(current_user)


@router.post("/login", response_model=TokenResponse | MfaChallengeResponse)
@_limiter.limit(settings.login_rate_limit)
def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    user = _find_user(db, payload.username, tenant_id)
    if not user or not user.active or not verify_password(payload.password, user.hashed_password):
        write_audit(
            db, user_id=user.id if user else None, action="login_failure",
            entity="users", entity_id=payload.username,
            after_data={"username": payload.username, "ip": request.client.host if request.client else "unknown"},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    record = db.get(UserMfa, user.id)
    if record and record.enabled:
        # The challenge is an authentication *stage*, not an access token. Its
        # nonce is stored hashed so even a valid challenge cannot be replayed.
        nonce = secrets.token_urlsafe(24)
        record.challenge_hash = hashlib.sha256(nonce.encode("ascii")).hexdigest()
        write_audit(db, user_id=user.id, action="mfa_challenge", entity="users",
                    entity_id=str(user.id))
        db.commit()
        return MfaChallengeResponse(
            challenge_token=create_mfa_challenge(user.id, tenant_id, user.session_version, nonce)
        )

    write_audit(
        db, user_id=user.id, action="login", entity="users", entity_id=str(user.id),
        after_data={"username": user.username, "ip": request.client.host if request.client else "unknown"},
    )
    db.commit()
    return _issue_tokens(user)


@router.post("/mfa/verify-login", response_model=TokenResponse)
@_limiter.limit("5/minute")
def verify_mfa_login(
    request: Request,
    payload: MfaLoginConfirm,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    try:
        claims = jwt.decode(payload.challenge_token, settings.secret_key, algorithms=[settings.algorithm])
        if claims.get("type") != "mfa_challenge" or int(claims["tenant"]) != tenant_id:
            raise _bad_mfa()
        user_id = int(claims["sub"])
        version = int(claims["ver"])
        nonce = str(claims["jti"])
    except (JWTError, ValueError, TypeError, KeyError) as exc:
        raise _bad_mfa() from exc
    user = _active_tenant_user(db, user_id, tenant_id)
    # Lock the MFA state while consuming TOTP/recovery codes; this prevents
    # two concurrent requests from redeeming the same challenge on PostgreSQL.
    record = (
        db.query(UserMfa).filter(UserMfa.user_id == user_id)
        .with_for_update().populate_existing().first()
        if user else None
    )
    if not user or user.session_version != version or not record or not record.enabled:
        raise _bad_mfa()
    expected = hashlib.sha256(nonce.encode("ascii")).hexdigest()
    if not secrets.compare_digest(record.challenge_hash or "", expected):
        raise _bad_mfa()
    if not consume_mfa_code(db, user, payload.code):
        write_audit(db, user_id=user.id, action="mfa_failure", entity="users", entity_id=str(user.id))
        db.commit()
        raise _bad_mfa()
    record.challenge_hash = None
    write_audit(db, user_id=user.id, action="mfa_login", entity="users", entity_id=str(user.id))
    db.commit()
    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    try:
        claims = jwt.decode(payload.refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        if claims.get("type") != "refresh":
            raise JWTError("invalid")
        user_id = int(claims["sub"])
        version = int(claims.get("ver", 0))
    except (JWTError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Refresh token inválido") from exc
    user = _active_tenant_user(db, user_id, tenant_id)
    if not user or user.session_version != version:
        raise HTTPException(status_code=401, detail="Refresh token inválido")
    return _issue_tokens(user)


@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Revokes all access and refresh tokens for the account by bumping its
    # version. Granular per-device sessions require a later session registry.
    current_user.session_version += 1
    record = db.get(UserMfa, current_user.id)
    if record:
        record.challenge_hash = None
    write_audit(
        db, user_id=current_user.id, action="logout", entity="users", entity_id=str(current_user.id),
        after_data={"all_sessions_revoked": True, "ip": request.client.host if request.client else "unknown"},
    )
    db.commit()
    return {"message": "Todas as sessões foram revogadas"}


@router.get("/mfa/status", response_model=MfaStatusResponse)
def mfa_status(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(UserMfa, current.id)
    remaining = db.query(MfaRecoveryCode).filter(MfaRecoveryCode.user_id == current.id).count()
    return MfaStatusResponse(enabled=bool(record and record.enabled), recovery_codes_remaining=remaining)


@router.post("/mfa/setup", response_model=MfaSetupResponse)
@_limiter.limit("5/minute")
def mfa_setup(
    request: Request,
    payload: MfaSetupRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current.hashed_password):
        raise HTTPException(status_code=401, detail="Senha atual inválida")
    record = db.get(UserMfa, current.id)
    if record and record.enabled:
        raise HTTPException(status_code=409, detail="MFA já ativado")
    secret = generate_totp_secret()
    if not record:
        record = UserMfa(user_id=current.id)
        db.add(record)
    record.encrypted_pending_secret = encrypt_secret(secret)
    record.pending_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    record.challenge_hash = None
    db.commit()
    # Never include the secret or URI in a log/audit record.
    return MfaSetupResponse(secret=secret, provisioning_uri=provisioning_uri(secret, current.username))


@router.post("/mfa/confirm", response_model=MfaConfirmResponse)
@_limiter.limit("5/minute")
def mfa_confirm(
    request: Request,
    payload: MfaCodeRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    record = (
        db.query(UserMfa).filter(UserMfa.user_id == current.id)
        .with_for_update().populate_existing().first()
    )
    if not record or record.enabled or not record.encrypted_pending_secret or not record.pending_expires_at:
        raise HTTPException(status_code=400, detail="Configuração MFA não iniciada")
    expiry = record.pending_expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Configuração MFA expirada")
    secret = decrypt_secret(record.encrypted_pending_secret)
    counter = valid_totp_counter(secret, payload.code)
    if counter is None:
        raise HTTPException(status_code=400, detail="Código MFA inválido")
    record.encrypted_secret = record.encrypted_pending_secret
    record.encrypted_pending_secret = None
    record.pending_expires_at = None
    record.enabled = True
    record.last_used_counter = counter
    codes = replace_recovery_codes(db, current.id)
    current.session_version += 1
    write_audit(db, user_id=current.id, action="mfa_enabled", entity="users", entity_id=str(current.id))
    db.commit()
    return MfaConfirmResponse(recovery_codes=codes)


@router.post("/mfa/disable")
@_limiter.limit("5/minute")
def mfa_disable(
    request: Request,
    payload: MfaDisableRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    record = (
        db.query(UserMfa).filter(UserMfa.user_id == current.id)
        .with_for_update().populate_existing().first()
    )
    if not record or not record.enabled or not consume_mfa_code(db, current, payload.code):
        raise HTTPException(status_code=401, detail="Código MFA inválido")
    db.query(MfaRecoveryCode).filter(MfaRecoveryCode.user_id == current.id).delete()
    db.delete(record)
    current.session_version += 1
    write_audit(db, user_id=current.id, action="mfa_disabled", entity="users", entity_id=str(current.id))
    db.commit()
    return {"message": "MFA desativado; todas as sessões foram revogadas"}


@router.post("/request-password-reset")
def request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    user = _find_user(db, payload.username, tenant_id)
    if not user or not user.active:
        return {"message": "Se usuário existir, o reset foi gerado"}
    token = secrets.token_urlsafe(24)
    reset = PasswordResetToken(
        user_id=user.id, token=token, expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)
    )
    db.add(reset)
    write_audit(db, user_id=user.id, action="create", entity="password_reset",
                entity_id=str(user.id), after_data={"issued": True})
    db.commit()
    response = {"message": "Se usuário existir, o reset foi gerado"}
    if settings.demo_mode:
        response = {"message": "Reset gerado para demo", "reset_token": token}
    return response


@router.post("/reset-password")
def reset_password(
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    reset = db.query(PasswordResetToken).filter(PasswordResetToken.token == payload.token).first()
    if not reset:
        raise HTTPException(status_code=400, detail="Token inválido/expirado")
    expiry = reset.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token inválido/expirado")
    user = _active_tenant_user(db, reset.user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido/expirado")
    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = False
    user.session_version += 1
    record = db.get(UserMfa, user.id)
    if record:
        record.challenge_hash = None
    db.delete(reset)
    write_audit(db, user_id=user.id, action="update", entity="users",
                entity_id=str(user.id), after_data={"password_reset": True, "all_sessions_revoked": True})
    db.commit()
    return {"message": "Senha atualizada"}
