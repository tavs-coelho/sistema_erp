"""Tenant resolution middleware.

Reads the ``Host`` request header, extracts the first subdomain component,
and resolves it to a ``TenantBranding.id`` by querying the database.  The
resolved ``tenant_id`` (defaulting to ``1`` when no matching tenant is found
or when accessed via ``localhost`` / ``127.0.0.1``) is stored on
``request.state.tenant_id`` so every downstream handler and dependency can
read it without repeating the lookup.

Routing logic
-------------
- ``prefeitura-a.erp.app``  → subdomain = ``"prefeitura-a"`` → look up tenant
- ``localhost:8000``         → no subdomain → tenant_id = 1 (default)
- ``127.0.0.1``              → no subdomain → tenant_id = 1 (default)
- ``erp.app`` (bare apex)   → no subdomain → tenant_id = 1 (default)
- ``unknown-slug.erp.app``  → subdomain found but no DB match → tenant_id = 1
"""

from __future__ import annotations

import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .db import SessionLocal
from .models import TenantBranding

# ---------------------------------------------------------------------------
# Per-tenant subdomain → tenant_id cache (avoids a DB lookup on every request)
# ---------------------------------------------------------------------------
_SUBDOMAIN_CACHE: dict[str, int] = {}
_SUBDOMAIN_CACHE_LOCK = threading.Lock()
_SUBDOMAIN_CACHE_TTL = 60  # seconds
_SUBDOMAIN_CACHE_TS: dict[str, float] = {}

_DEFAULT_TENANT_ID = 1
# Host values that indicate a local / direct access (no real subdomain)
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


def _resolve_subdomain(host: str) -> str | None:
    """Extract the first subdomain label from ``host``, or ``None``."""
    # Strip port
    bare = host.split(":")[0]
    if bare in _LOCAL_HOSTS:
        return None
    parts = bare.split(".")
    # "erp.app" → 2 parts → no subdomain
    # "prefeitura-a.erp.app" → 3+ parts → first part is the subdomain
    if len(parts) >= 3:
        return parts[0]
    return None


def _lookup_tenant(subdomain: str) -> int:
    """Return the tenant_id for *subdomain*, querying DB if not cached."""
    now = time.monotonic()
    with _SUBDOMAIN_CACHE_LOCK:
        cached_ts = _SUBDOMAIN_CACHE_TS.get(subdomain, 0.0)
        if subdomain in _SUBDOMAIN_CACHE and (now - cached_ts) < _SUBDOMAIN_CACHE_TTL:
            return _SUBDOMAIN_CACHE[subdomain]

    db = SessionLocal()
    try:
        row = db.query(TenantBranding).filter(TenantBranding.subdomain == subdomain).first()
        tenant_id = row.id if row else _DEFAULT_TENANT_ID
    finally:
        db.close()

    with _SUBDOMAIN_CACHE_LOCK:
        _SUBDOMAIN_CACHE[subdomain] = tenant_id
        _SUBDOMAIN_CACHE_TS[subdomain] = now

    return tenant_id


def invalidate_tenant_cache(subdomain: str | None = None) -> None:
    """Evict one or all entries from the subdomain resolution cache.

    Called by the tenant management endpoints after creating or updating a
    tenant so that the next request sees the fresh DB row.
    """
    with _SUBDOMAIN_CACHE_LOCK:
        if subdomain is None:
            _SUBDOMAIN_CACHE.clear()
            _SUBDOMAIN_CACHE_TS.clear()
        else:
            _SUBDOMAIN_CACHE.pop(subdomain, None)
            _SUBDOMAIN_CACHE_TS.pop(subdomain, None)


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve the current tenant from the ``Host`` request header.

    Sets ``request.state.tenant_id`` (int) before the request reaches any
    router handler.  All tenant-aware dependencies and queries should read
    this value via the ``get_tenant_id`` FastAPI dependency in ``deps.py``.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        host = request.headers.get("host", "localhost")
        subdomain = _resolve_subdomain(host)
        if subdomain:
            request.state.tenant_id = _lookup_tenant(subdomain)
        else:
            request.state.tenant_id = _DEFAULT_TENANT_ID
        return await call_next(request)
