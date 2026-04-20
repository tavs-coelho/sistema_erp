"""Branding / white-label router.

Endpoints:
  GET  /branding        — public, returns current tenant branding settings
  PUT  /branding        — admin-only, updates branding settings
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import require_roles
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
# Simple in-process cache with TTL (avoids a DB round-trip on every page load)
# ---------------------------------------------------------------------------
_CACHE_TTL = 300  # seconds
_cache: BrandingOut | None = None
_cache_ts: float = 0.0


def _invalidate_cache() -> None:
    global _cache, _cache_ts
    _cache = None
    _cache_ts = 0.0


def _get_or_create(db: Session) -> TenantBranding:
    """Return the single branding row (id=1), creating it with defaults if absent."""
    row = db.get(TenantBranding, 1)
    if not row:
        row = TenantBranding(id=1, **_DEFAULTS)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=BrandingOut)
def get_branding(db: Session = Depends(get_db)):
    """Public endpoint — no authentication required.

    Returns the current branding configuration so the frontend can apply
    theme colours, org name, logo and title on every page load.
    Responses are cached in-process for up to 5 minutes to avoid repeated
    database round-trips on every page navigation.
    """
    global _cache, _cache_ts
    now = time.monotonic()
    if _cache is not None and (now - _cache_ts) < _CACHE_TTL:
        return _cache
    row = _get_or_create(db)
    _cache = BrandingOut.model_validate(row)
    _cache_ts = now
    return _cache


@router.put("", response_model=BrandingOut)
def update_branding(
    payload: BrandingUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin)),
):
    """Admin-only endpoint to update the tenant branding settings."""
    row = _get_or_create(db)
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
        entity_id="1",
        before_data=before,
        after_data=payload.model_dump(exclude_none=True),
    )
    db.commit()
    db.refresh(row)
    _invalidate_cache()
    return row
