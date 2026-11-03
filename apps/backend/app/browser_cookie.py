"""Opt-in browser session cookies and signed double-submit CSRF.

A browser cannot read HttpOnly bearer tokens. Mutating requests authenticated by
cookies must present a signed CSRF value in a custom header, plus a same-origin
Origin header. API clients using explicit Bearer authentication retain their
existing contracts.
"""
import hashlib
import hmac
import re
import secrets
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import settings
from .schemas import TokenResponse

ACCESS_COOKIE = "erp_access"
REFRESH_COOKIE = "erp_refresh"
CSRF_COOKIE = "erp_csrf"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,64}$")
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def browser_auth_enabled() -> None:
    if not settings.browser_cookie_auth_enabled:
        raise HTTPException(status_code=404, detail="Fluxo de navegador indisponível")


def _host(request: Request) -> str:
    return request.headers.get("host", "").lower()


def _signature(request: Request, nonce: str) -> str:
    payload = (nonce + "|" + _host(request)).encode("utf-8")
    return hmac.new(settings.secret_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def issue_csrf(request: Request, response: Response) -> str:
    nonce = secrets.token_urlsafe(24)
    token = nonce + "." + _signature(request, nonce)
    response.set_cookie(
        CSRF_COOKIE, token, httponly=False,
        secure=settings.browser_cookie_secure, samesite="strict", path="/",
        max_age=settings.refresh_token_minutes * 60,
    )
    response.headers["Cache-Control"] = "no-store"
    return token


def require_csrf(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        raise HTTPException(status_code=403, detail="Origem ausente")
    source = urlsplit(origin)
    if (
        source.scheme not in {"http", "https"}
        or source.netloc.lower() != _host(request)
        or (settings.browser_cookie_secure and source.scheme != "https")
    ):
        raise HTTPException(status_code=403, detail="Origem inválida")

    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="CSRF inválido")
    parts = cookie.split(".")
    if len(parts) != 2 or not _TOKEN_RE.fullmatch(parts[0]) or len(parts[1]) != 64:
        raise HTTPException(status_code=403, detail="CSRF inválido")
    if not hmac.compare_digest(parts[1], _signature(request, parts[0])):
        raise HTTPException(status_code=403, detail="CSRF inválido")


def set_session_cookies(response: Response, tokens: TokenResponse) -> None:
    response.set_cookie(
        ACCESS_COOKIE, tokens.access_token, httponly=True,
        secure=settings.browser_cookie_secure, samesite="strict", path="/",
        max_age=settings.access_token_minutes * 60,
    )
    response.set_cookie(
        REFRESH_COOKIE, tokens.refresh_token, httponly=True,
        secure=settings.browser_cookie_secure, samesite="strict",
        path="/",  # works on both /api proxy and direct FastAPI routes
        max_age=settings.refresh_token_minutes * 60,
    )
    response.headers["Cache-Control"] = "no-store"


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/", secure=settings.browser_cookie_secure, samesite="strict")
    response.delete_cookie(REFRESH_COOKIE, path="/", secure=settings.browser_cookie_secure, samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=settings.browser_cookie_secure, samesite="strict")
    response.headers["Cache-Control"] = "no-store"


class CsrfCookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.browser_cookie_auth_enabled or request.method not in _UNSAFE_METHODS:
            return await call_next(request)
        # Browser login / refresh / logout always require CSRF. Other routes
        # require it only when using cookie auth rather than explicit Bearer.
        browser_endpoint = request.url.path.startswith("/auth/browser/")
        bearer = request.headers.get("authorization", "")
        explicit_bearer = bearer.lower().startswith("bearer ") and bool(bearer[7:].strip())
        cookie_auth = ACCESS_COOKIE in request.cookies or REFRESH_COOKIE in request.cookies
        if browser_endpoint or (cookie_auth and not explicit_bearer):
            try:
                require_csrf(request)
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        return await call_next(request)
