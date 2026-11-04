"""Operational readiness and security response metadata for the API."""
from contextvars import ContextVar
from uuid import uuid4

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .db import SessionLocal

router = APIRouter(tags=["platform-health"])
request_id: ContextVar[str] = ContextVar("request_id", default="")


@router.get("/health/live")
def liveness():
    """Process is serving HTTP; no internal metadata is exposed."""
    return {"status": "alive"}


@router.get("/health/ready")
def readiness(response: Response):
    """Database-backed readiness probe. 503 blocks traffic until DB is ready."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar_one()
        return {"status": "ready"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}


class ApiSecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        supplied = request.headers.get("x-request-id", "")
        # Never reflect attacker-controlled newlines or arbitrarily long values.
        rid = supplied if 1 <= len(supplied) <= 64 and all(
            ch.isascii() and (ch.isalnum() or ch in "-_") for ch in supplied
        ) else uuid4().hex
        token = request_id.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id.reset(token)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # These API endpoints can contain personal or contractual information.
        # Never store them in intermediary/browser caches.
        if request.url.path.startswith((
            "/auth", "/core", "/protocolo", "/accounting", "/hr",
            "/procurement", "/patrimony",
        )):
            response.headers["Cache-Control"] = "no-store"
        return response
