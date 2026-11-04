"""Browser-only auth transport: HttpOnly cookies, CSRF, and refresh rotation.

Existing /auth/* bearer endpoints remain backward-compatible for API clients.
This router never returns access or refresh tokens in JSON.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..browser_cookie import (
    REFRESH_COOKIE, browser_auth_enabled, clear_session_cookies,
    issue_csrf, set_session_cookies,
)
from ..db import get_db
from ..deps import get_access_token, get_current_user, get_tenant_id
from ..models import User
from ..schemas import (
    AuthMeResponse, LoginRequest, MfaChallengeResponse, MfaLoginConfirm,
    RefreshRequest, TokenResponse,
)
from . import auth

router = APIRouter(prefix="/auth/browser", tags=["auth-browser"])


@router.get("/csrf")
def csrf(request: Request, response: Response):
    browser_auth_enabled()
    token = issue_csrf(request, response)
    return {"csrf_token": token}


@router.post("/login")
def browser_login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    browser_auth_enabled()
    result = auth.login(request, payload, db, tenant_id)
    if isinstance(result, MfaChallengeResponse):
        return result.model_dump()
    set_session_cookies(response, result)
    return {"role": result.role, "must_change_password": result.must_change_password}


@router.post("/mfa/verify-login")
def browser_mfa_login(
    request: Request,
    response: Response,
    payload: MfaLoginConfirm,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    browser_auth_enabled()
    result = auth.verify_mfa_login(request, payload, db, tenant_id)
    set_session_cookies(response, result)
    return {"role": result.role, "must_change_password": result.must_change_password}


@router.post("/refresh")
def browser_refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    browser_auth_enabled()
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    tokens = auth.refresh(RefreshRequest(refresh_token=refresh_token), request, db, tenant_id)
    set_session_cookies(response, tokens)
    return {"role": tokens.role, "must_change_password": tokens.must_change_password}


@router.get("/me", response_model=AuthMeResponse)
def browser_me(current_user: User = Depends(get_current_user)):
    browser_auth_enabled()
    return AuthMeResponse.model_validate(current_user)


@router.post("/logout")
def browser_logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    browser_auth_enabled()
    auth.logout(request, current_user, token, db, tenant_id)
    clear_session_cookies(response)
    return {"message": "Sessão encerrada"}


@router.post("/logout-all")
def browser_logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    browser_auth_enabled()
    auth.logout_all(current_user, db)
    clear_session_cookies(response)
    return {"message": "Todas as sessões encerradas"}


@router.post("/clear")
def clear_expired_browser_session(response: Response):
    """Clear expired browser cookies even when the former access token is invalid.

    The CSRF middleware requires a valid signed same-origin double-submit token.
    This endpoint never creates or revives a server-side session.
    """
    browser_auth_enabled()
    clear_session_cookies(response)
    return {"message": "Cookies de sessão encerrados"}
