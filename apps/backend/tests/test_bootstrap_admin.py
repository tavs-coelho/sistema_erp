"""Production bootstrap must create one admin without demo credentials or public API."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import RoleEnum, TenantBranding, User
from app.security import verify_password
from scripts.bootstrap_admin import create_first_administrator


@pytest.fixture
def db():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def test_creates_first_admin_with_secure_hash(db):
    admin = create_first_administrator(
        db, username="initial-admin", email="initial@example.org",
        password="strong-initial-password-#1", organization="Município Operacional",
    )
    assert admin.id > 0
    assert admin.role == RoleEnum.admin
    assert admin.tenant_id == 1
    assert admin.must_change_password is True
    assert verify_password("strong-initial-password-#1", admin.hashed_password)
    assert "strong-initial-password" not in admin.hashed_password
    assert db.get(TenantBranding, 1).org_name == "Município Operacional"


def test_refuses_second_administrator_on_nonempty_db(db):
    args = dict(username="initial-admin", email="initial@example.org",
                password="strong-initial-password-#1", organization="Município Operacional")
    create_first_administrator(db, **args)
    with pytest.raises(ValueError, match="já possui usuários"):
        create_first_administrator(db, **{**args, "username": "second-admin"})
    assert db.query(User).count() == 1


@pytest.mark.parametrize("username,email,password,organization", [
    ("x", "valid@example.org", "strong-initial-password-#1", "Cidade"),
    ("initial", "invalid", "strong-initial-password-#1", "Cidade"),
    ("initial", "valid@example.org", "demo123", "Cidade"),
    ("initial", "valid@example.org", "strong-initial-password-#1", "A"),
])
def test_rejects_unsafe_bootstrap(db, username, email, password, organization):
    with pytest.raises(ValueError):
        create_first_administrator(
            db, username=username, email=email, password=password, organization=organization,
        )
    assert db.query(User).count() == 0
