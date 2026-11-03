"""Device session and rotating refresh token integration regressions."""
from datetime import timedelta
import hashlib

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.deps import get_tenant_id
from app.limiter import limiter
from app.main import app
from app.models import RoleEnum, TenantBranding, User, UserSession
from app.security import create_access_token, create_refresh_token, hash_password
from app.session_service import utc_now


@pytest.fixture
def session_client():
    limiter._storage.reset()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as db:
        db.add_all([
            TenantBranding(id=1, subdomain="cidade-um"),
            TenantBranding(id=2, subdomain="cidade-dois"),
            User(id=101, username="session-one", full_name="User One",
                 email="one-session@example.org", role=RoleEnum.admin,
                 hashed_password=hash_password("password-session-one"),
                 tenant_id=1, active=True, session_version=0),
            User(id=202, username="session-two", full_name="User Two",
                 email="two-session@example.org", role=RoleEnum.admin,
                 hashed_password=hash_password("password-session-two"),
                 tenant_id=2, active=True, session_version=0),
        ])
        db.commit()

    def override_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = lambda: 1
    client = TestClient(app)
    try:
        yield client, session_factory, lambda t: app.dependency_overrides.__setitem__(
            get_tenant_id, lambda: t
        )
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_tenant_id, None)
        engine.dispose()


def login(client, username="session-one", password="password-session-one", agent="Test Device"):
    result = client.post("/auth/login", headers={"User-Agent": agent},
                         json={"username": username, "password": password})
    assert result.status_code == 200, result.text
    return result.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def claims(token):
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def test_two_devices_and_list_do_not_expose_refresh_tokens(session_client):
    client, factory, _ = session_client
    first = login(client, agent="Laptop")
    second = login(client, agent="Mobile")
    one = claims(first["access_token"])
    two = claims(second["access_token"])
    assert len(one["sid"]) == 32 and one["sid"] != two["sid"]
    sessions = client.get("/auth/sessions", headers=auth(first["access_token"]))
    assert sessions.status_code == 200
    items = sessions.json()
    assert len(items) == 2
    assert sum(int(item["current"]) for item in items) == 1
    assert {item["user_agent"] for item in items} == {"Laptop", "Mobile"}
    assert "refresh_token" not in str(items)
    with factory() as db:
        record = db.get(UserSession, one["sid"])
        assert record and record.refresh_token_hash == hashlib.sha256(
            first["refresh_token"].encode()
        ).hexdigest()
        assert first["refresh_token"] not in str(record.__dict__)


def test_refresh_rotation_replay_revokes_only_one_device(session_client):
    client, factory, _ = session_client
    first = login(client, agent="First")
    second = login(client, agent="Second")
    old = first["refresh_token"]
    rotated = client.post("/auth/refresh", json={"refresh_token": old})
    assert rotated.status_code == 200
    newer = rotated.json()["refresh_token"]
    assert newer != old
    assert claims(newer)["sid"] == claims(old)["sid"]
    assert client.post("/auth/refresh", json={"refresh_token": newer}).status_code == 200

    replay = client.post("/auth/refresh", json={"refresh_token": old})
    assert replay.status_code == 401
    assert client.get("/auth/me", headers=auth(first["access_token"])).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": newer}).status_code == 401
    assert client.get("/auth/me", headers=auth(second["access_token"])).status_code == 200
    with factory() as db:
        assert db.get(UserSession, claims(old)["sid"]).revoked_at is not None


def test_current_device_logout_preserves_other_device(session_client):
    client, _, _ = session_client
    first = login(client)
    second = login(client)
    response = client.post("/auth/logout", headers=auth(first["access_token"]))
    assert response.status_code == 200
    assert client.get("/auth/me", headers=auth(first["access_token"])).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
    assert client.get("/auth/me", headers=auth(second["access_token"])).status_code == 200
    remaining = client.get("/auth/sessions", headers=auth(second["access_token"]))
    assert len(remaining.json()) == 1


def test_remove_other_device_and_logout_all(session_client):
    client, _, _ = session_client
    first = login(client)
    second = login(client)
    third = login(client)
    sid = claims(first["access_token"])["sid"]
    removed = client.delete(f"/auth/sessions/{sid}", headers=auth(second["access_token"]))
    assert removed.status_code == 200
    assert client.get("/auth/me", headers=auth(first["access_token"])).status_code == 401
    assert client.get("/auth/me", headers=auth(second["access_token"])).status_code == 200
    all_out = client.post("/auth/logout-all", headers=auth(second["access_token"]))
    assert all_out.status_code == 200
    for tokens in (second, third):
        assert client.get("/auth/me", headers=auth(tokens["access_token"])).status_code == 401
        assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert login(client)["access_token"]


def test_cross_tenant_cannot_list_or_revoke_device(session_client):
    client, _, set_tenant = session_client
    one = login(client)
    set_tenant(2)
    two = login(client, username="session-two", password="password-session-two")
    sid = claims(one["access_token"])["sid"]
    assert client.delete(f"/auth/sessions/{sid}", headers=auth(two["access_token"])).status_code == 404
    assert client.post("/auth/refresh", json={"refresh_token": one["refresh_token"]}).status_code == 401
    assert client.get("/auth/me", headers=auth(one["access_token"])).status_code == 401
    assert client.get("/auth/sessions", headers=auth(two["access_token"])).status_code == 200
    assert {s["id"] for s in client.get("/auth/sessions", headers=auth(two["access_token"])).json()} == {claims(two["access_token"])["sid"]}
    set_tenant(1)
    assert client.get("/auth/me", headers=auth(one["access_token"])).status_code == 200


def test_expired_session_denies_access_and_refresh(session_client):
    client, factory, _ = session_client
    tokens = login(client)
    with factory() as db:
        session = db.get(UserSession, claims(tokens["access_token"])["sid"])
        session.expires_at = utc_now() - timedelta(minutes=1)
        db.commit()
    assert client.get("/auth/me", headers=auth(tokens["access_token"])).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_production_rejects_sidless_legacy_tokens(session_client, monkeypatch):
    client, _, _ = session_client
    legacy_access = create_access_token(101, "admin")
    legacy_refresh = create_refresh_token(101, "admin")
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.get("/auth/me", headers=auth(legacy_access)).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": legacy_refresh}).status_code == 401


def test_password_reset_revokes_all_devices(session_client):
    client, factory, _ = session_client
    first = login(client)
    second = login(client)
    reset = client.post("/auth/request-password-reset", json={"username": "session-one"})
    assert reset.status_code == 200
    with factory() as db:
        from app.models import PasswordResetToken
        code = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == 101).first().token
    result = client.post("/auth/reset-password", json={
        "token": code, "new_password": "password-session-new"
    })
    assert result.status_code == 200
    for token in (first, second):
        assert client.get("/auth/me", headers=auth(token["access_token"])).status_code == 401
    with factory() as db:
        assert db.query(UserSession).filter(
            UserSession.user_id == 101, UserSession.revoked_at.is_(None)
        ).count() == 0
