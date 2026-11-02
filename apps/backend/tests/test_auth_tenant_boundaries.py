"""Regression tests for authentication isolation between municipal tenants.

Uses an independent in-memory database; no demonstration users or credentials.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.deps import get_tenant_id
from app.main import app
from app.models import AuditLog, PasswordResetToken, RoleEnum, TenantBranding, User
from app.security import create_access_token, create_refresh_token, hash_password, verify_password


@pytest.fixture
def tenant_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as db:
        db.add_all([
            TenantBranding(id=1, subdomain="cidade-um", org_name="Cidade Um"),
            TenantBranding(id=2, subdomain="cidade-dois", org_name="Cidade Dois"),
            User(
                id=101, username="tenant-one", full_name="Tenant One",
                email="one@example.invalid", hashed_password=hash_password("test-password-1"),
                role=RoleEnum.admin, tenant_id=1, active=True,
            ),
            User(
                id=202, username="tenant-two", full_name="Tenant Two",
                email="two@example.invalid", hashed_password=hash_password("test-password-2"),
                role=RoleEnum.admin, tenant_id=2, active=True,
            ),
            User(
                id=303, username="inactive-user", full_name="Inactive User",
                email="disabled@example.invalid", hashed_password=hash_password("test-password-3"),
                role=RoleEnum.admin, tenant_id=1, active=False,
            ),
            User(
                id=404, username="legacy-user", full_name="Legacy User",
                email="legacy@example.invalid", hashed_password=hash_password("test-password-4"),
                role=RoleEnum.admin, tenant_id=None, active=True,
            ),
        ])
        db.commit()

    def override_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = lambda: 1
    client = TestClient(app)  # No lifespan: avoid global demo seed.
    try:
        yield client, session_factory, lambda tenant: app.dependency_overrides.__setitem__(
            get_tenant_id, lambda: tenant
        )
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_tenant_id, None)
        engine.dispose()


def test_access_token_cannot_be_used_in_another_tenant(tenant_client):
    client, _, set_tenant = tenant_client
    token = create_access_token(101, "admin")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    set_tenant(2)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.get("/core/users", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_refresh_token_cannot_be_used_in_another_tenant(tenant_client):
    client, _, set_tenant = tenant_client
    token = create_refresh_token(101, "admin")
    set_tenant(2)
    assert client.post("/auth/refresh", json={"refresh_token": token}).status_code == 401
    set_tenant(1)
    assert client.post("/auth/refresh", json={"refresh_token": token}).status_code == 200


def test_inactive_user_cannot_log_in_or_use_existing_tokens(tenant_client):
    client, _, _ = tenant_client
    assert client.post(
        "/auth/login", json={"username": "inactive-user", "password": "test-password-3"}
    ).status_code == 401
    access = create_access_token(303, "admin")
    refresh = create_refresh_token(303, "admin")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_reset_confirmation_cannot_cross_tenant(tenant_client):
    client, session_factory, set_tenant = tenant_client
    with session_factory() as db:
        db.add(PasswordResetToken(
            user_id=101, token="isolated-reset-token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        ))
        db.commit()
    set_tenant(2)
    response = client.post("/auth/reset-password", json={
        "token": "isolated-reset-token", "new_password": "new-password"
    })
    assert response.status_code == 400
    with session_factory() as db:
        user = db.get(User, 101)
        assert verify_password("test-password-1", user.hashed_password)
        assert db.query(PasswordResetToken).count() == 1


def test_expired_reset_token_rejected_without_timezone_error(tenant_client):
    client, session_factory, _ = tenant_client
    with session_factory() as db:
        db.add(PasswordResetToken(
            user_id=101, token="expired-reset-token",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        ))
        db.commit()
    response = client.post("/auth/reset-password", json={
        "token": "expired-reset-token", "new_password": "new-password"
    })
    assert response.status_code == 400


def test_reset_success_and_one_time_use(tenant_client):
    client, session_factory, _ = tenant_client
    with session_factory() as db:
        db.add(PasswordResetToken(
            user_id=101, token="valid-reset-token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        ))
        db.commit()
    payload = {"token": "valid-reset-token", "new_password": "new-password"}
    assert client.post("/auth/reset-password", json=payload).status_code == 200
    assert client.post("/auth/reset-password", json=payload).status_code == 400
    with session_factory() as db:
        assert verify_password("new-password", db.get(User, 101).hashed_password)


def test_legacy_default_tenant_user_retains_access(tenant_client):
    client, _, set_tenant = tenant_client
    token = create_access_token(404, "admin")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    set_tenant(2)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_user_management_is_scoped_to_current_tenant(tenant_client):
    client, session_factory, set_tenant = tenant_client
    one_token = create_access_token(101, "admin")
    one_headers = {"Authorization": f"Bearer {one_token}"}
    one_users = client.get("/core/users", headers=one_headers)
    assert one_users.status_code == 200
    assert {u["id"] for u in one_users.json()} == {101, 303, 404}

    set_tenant(2)
    two_token = create_access_token(202, "admin")
    two_headers = {"Authorization": f"Bearer {two_token}"}
    two_users = client.get("/core/users", headers=two_headers)
    assert two_users.status_code == 200
    assert {u["id"] for u in two_users.json()} == {202}

    cross_update = client.patch(
        "/core/users/101", json={"full_name": "Should Not Change"}, headers=two_headers
    )
    assert cross_update.status_code == 404
    with session_factory() as db:
        assert db.get(User, 101).full_name == "Tenant One"

    new_user = client.post(
        "/core/users",
        json={
            "username": "new-tenant-two", "full_name": "Created in Tenant Two",
            "email": "new2@example.com", "role": "read_only",
            "password": "test-password-new",
        },
        headers=two_headers,
    )
    assert new_user.status_code == 200
    with session_factory() as db:
        assert db.get(User, new_user.json()["id"]).tenant_id == 2


def test_audit_trail_is_scoped_to_tenant(tenant_client):
    client, session_factory, set_tenant = tenant_client
    with session_factory() as db:
        db.add_all([
            AuditLog(user_id=101, action="create", entity="tenant-one-only", entity_id="101"),
            AuditLog(user_id=202, action="create", entity="tenant-two-only", entity_id="202"),
        ])
        db.commit()

    token_one = create_access_token(101, "admin")
    one = client.get("/core/audit-logs", headers={"Authorization": f"Bearer {token_one}"})
    assert one.status_code == 200
    assert {log["entity"] for log in one.json()["items"]} == {"tenant-one-only"}

    set_tenant(2)
    token_two = create_access_token(202, "admin")
    two = client.get("/core/audit-logs", headers={"Authorization": f"Bearer {token_two}"})
    assert two.status_code == 200
    assert {log["entity"] for log in two.json()["items"]} == {"tenant-two-only"}
