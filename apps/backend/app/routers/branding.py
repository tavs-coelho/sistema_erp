"""Branding / white-label router.

Endpoints:
  GET  /branding        — public, returns current tenant branding settings
  PUT  /branding        — admin-only, updates branding settings
"""

import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_tenant_id, require_roles
from ..models import RoleEnum, TenantBranding, User
from ..schemas import BrandingOut, BrandingUpdate

router = APIRouter(prefix="/branding", tags=["branding"])

_DEFAULTS = {
    "org_name": "Prefeitura Municipal",
    "logo_url": "",
    "primary_color": "#1d4ed8",
    "secondary_color": "#0f172a",
    "accent_color": "#0ea5e9",
    "favicon_url": "/favicon.ico",
    "app_title": "Sistema ERP Municipal",
}

# ---------------------------------------------------------------------------
# Per-tenant in-process cache with TTL (avoids a DB round-trip on every page load)
# Keyed by tenant_id so different tenants get independent cached values.
# ---------------------------------------------------------------------------
_CACHE_TTL = 300  # seconds
_cache: dict[int, BrandingOut] = {}
_cache_ts: dict[int, float] = {}


def _invalidate_cache(tenant_id: int | None = None) -> None:
    if tenant_id is None:
        _cache.clear()
        _cache_ts.clear()
    else:
        _cache.pop(tenant_id, None)
        _cache_ts.pop(tenant_id, None)


def _get_or_create(db: Session, tenant_id: int) -> TenantBranding:
    """Return the branding row for *tenant_id*, creating it with defaults if absent."""
    row = db.get(TenantBranding, tenant_id)
    if not row:
        row = TenantBranding(id=tenant_id, **_DEFAULTS)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=BrandingOut)
def get_branding(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    """Public endpoint — no authentication required.

    Returns the branding configuration for the current tenant so the
    frontend can apply theme colours, org name, logo and title on every
    page load.  Responses are cached in-process per tenant for up to 5
    minutes to avoid repeated database round-trips on every page navigation.
    """
    now = time.monotonic()
    if tenant_id in _cache and (now - _cache_ts.get(tenant_id, 0.0)) < _CACHE_TTL:
        return _cache[tenant_id]
    row = _get_or_create(db, tenant_id)
    _cache[tenant_id] = BrandingOut.model_validate(row)
    _cache_ts[tenant_id] = now
    return _cache[tenant_id]


@router.put("", response_model=BrandingOut)
def update_branding(
    payload: BrandingUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    current: User = Depends(require_roles(RoleEnum.admin)),
):
    """Admin-only endpoint to update the tenant branding settings."""
    row = _get_or_create(db, tenant_id)
    before: dict = {
        "org_name": row.org_name,
        "primary_color": row.primary_color,
        "secondary_color": row.secondary_color,
        "accent_color": row.accent_color,
    }
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    write_audit(
        db,
        user_id=current.id,
        action="update",
        entity="tenant_branding",
        entity_id=str(tenant_id),
        before_data=before,
        after_data=payload.model_dump(exclude_none=True),
    )
    db.commit()
    db.refresh(row)
    _invalidate_cache(tenant_id)
    return row
