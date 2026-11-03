"""Browser cookie authentication, CSRF and MFA regression tests.

The cookie transport is opt-in and must never return bearer tokens in JSON.
No production credentials are used; all data lives in isolated in-memory SQLite.
"""
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, settings
from app.db import Base, get_db
from app.deps import get_tenant_id
from app.limiter import limiter
from app.main import app
from app.mfa import totp_at
from app.models import RoleEnum, TenantBranding, User, UserSession
from app.security import hash_password


@pytest.fixture
def browser_client(monkeypatch):
    limiter._storage.reset()
    monkeypatch.setattr(settings, "browser_cookie_auth_enabled", True)
    monkeypatch.setattr(settings, "browser_cookie_secure", False)
    monkeypatch.setattr(settings, "mfa_encryption_key", Fernet.generate_key().decode("ascii"))
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        db.add_all([
            TenantBranding(id=1, subdomain="first"),
            TenantBranding(id=2, subdomain="second"),
            User(
                id=10, username="cookie-one", full_name="First User",
                email="cookie-one@example.org", role=RoleEnum.admin,
                hashed_password=hash_password("first-test-password"),
                tenant_id=1, active=True, session_version=0,
            ),
            User(
                id=20, username="cookie-two", full_name="Second User",
                email="cookie-two@example.org", role=RoleEnum.admin,
                hashed_password=hash_password("second-test-password"),
                tenant_id=2, active=True, session_version=0,
            ),
        ])
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = lambda: 1
    # Do not run the app lifespan: demo startup may seed the global database.
    client = TestClient(app, base_url="https://testserver")
    try:
        yield client, factory, lambda tenant: app.dependency_overrides.__setitem__(
            get_tenant_id, lambda: tenant
        )
    finally:
        client.close()
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_tenant_id, None)
    engine.dispose()


def headers(csrf_token: str) -> dict:
    return {"Origin": "https://testserver", "X-CSRF-Token": csrf_token}


def get_csrf(client):
    response = client.get("/auth/browser/csrf")
    assert response.status_code == 200
    token = response.json()["csrf_token"]
    assert token == client.cookies.get("erp_csrf")
    return token


def login(client, csrf):
    return client.post(
        "/auth/browser/login", headers=headers(csrf),
        json={"username": "cookie-one", "password": "first-test-password"},
    )


def test_opt_in_off_preserves_bearer_only_mode(browser_client, monkeypatch):
    client, _, _ = browser_client
    monkeypatch.setattr(settings, "browser_cookie_auth_enabled", False)
    assert client.get("/auth/browser/csrf").status_code == 404
    api_login = client.post(
        "/auth/login", json={"username": "cookie-one", "password": "first-test-password"},
    )
    assert api_login.status_code == 200
    assert "access_token" in api_login.json()
    assert client.get(
        "/auth/me", headers={"Authorization": f"Bearer {api_login.json()['access_token']}"},
    ).status_code == 200


def test_browser_login_sets_httponly_cookies_without_json_bearers(browser_client):
    client, factory, _ = browser_client
    csrf = get_csrf(client)
    response = login(client, csrf)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"role", "must_change_password"}
    assert "token" not in str(payload).lower()
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 2
    for value in cookies:
        assert "httponly" in value.lower()
        assert "samesite=strict" in value.lower()
    assert client.get("/auth/browser/me").status_code == 200
    assert client.get("/auth/me").status_code == 200
    with factory() as db:
        assert db.query(UserSession).filter(UserSession.user_id == 10).count() == 1


def test_csrf_required_for_login_and_cookie_based_writes(browser_client):
    client, _, _ = browser_client
    csrf = get_csrf(client)
    data = {"username": "cookie-one", "password": "first-test-password"}
    assert client.post("/auth/browser/login", json=data).status_code == 403
    assert client.post(
        "/auth/browser/login", headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf}, json=data
    ).status_code == 403
    assert client.post(
        "/auth/browser/login", headers={"Origin": "https://testserver", "X-CSRF-Token": "wrong"}, json=data
    ).status_code == 403

    assert login(client, csrf).status_code == 200
    assert client.post("/auth/logout").status_code == 403
    assert client.post("/auth/logout", headers=headers(csrf)).status_code == 200
    assert client.get("/auth/browser/me").status_code == 401


def test_signed_double_submit_rejects_forged_token(browser_client):
    client, _, _ = browser_client
    client.cookies.set("erp_csrf", "A" * 32 + "." + "0" * 64)
    forged = "A" * 32 + "." + "0" * 64
    response = client.post(
        "/auth/browser/login", headers=headers(forged),
        json={"username": "cookie-one", "password": "first-test-password"},
    )
    assert response.status_code == 403


def test_browser_refresh_rotates_cookie_and_replay_revokes_device(browser_client):
    client, factory, _ = browser_client
    csrf = get_csrf(client)
    assert login(client, csrf).status_code == 200
    old_refresh = client.cookies.get("erp_refresh")
    assert old_refresh
    response = client.post("/auth/browser/refresh", headers=headers(csrf))
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"role", "must_change_password"}
    new_refresh = client.cookies.get("erp_refresh")
    assert new_refresh and new_refresh != old_refresh
    # Simulate a stolen pre-rotation credential. Replay revokes this device.
    client.cookies.set("erp_refresh", old_refresh)
    assert client.post("/auth/browser/refresh", headers=headers(csrf)).status_code == 401
    assert client.get("/auth/browser/me").status_code == 401
    with factory() as db:
        assert db.query(UserSession).filter(
            UserSession.user_id == 10, UserSession.revoked_at.isnot(None),
        ).count() == 1


def test_cookie_session_cannot_cross_tenant(browser_client):
    client, _, set_tenant = browser_client
    csrf = get_csrf(client)
    assert login(client, csrf).status_code == 200
    set_tenant(2)
    assert client.get("/auth/browser/me").status_code == 401
    assert client.post("/auth/browser/refresh", headers=headers(csrf)).status_code == 401
    set_tenant(1)
    assert client.get("/auth/browser/me").status_code == 200


def test_browser_logout_all_clears_auth_and_csrf_cookies(browser_client):
    client, _, _ = browser_client
    csrf = get_csrf(client)
    assert login(client, csrf).status_code == 200
    response = client.post("/auth/browser/logout-all", headers=headers(csrf))
    assert response.status_code == 200
    assert not client.cookies.get("erp_access")
    assert not client.cookies.get("erp_refresh")
    assert not client.cookies.get("erp_csrf")
    assert client.get("/auth/browser/me").status_code == 401


def test_production_requires_secure_cookies():
    with pytest.raises(ValidationError, match="Secure cookies"):
        Settings(
            demo_mode=False, secret_key="a" * 48,
            database_url="sqlite:///./unused.db",
            cors_allowed_origins="https://erp.example.org",
            browser_cookie_auth_enabled=True,
            browser_cookie_secure=False,
        )


def test_cookies_never_authorize_mfa_challenge_as_access(browser_client):
    client, _, _ = browser_client
    csrf = get_csrf(client)
    assert login(client, csrf).status_code == 200
    # A token signed for a different purpose is not a user session.
    valid_access = client.cookies.get("erp_access")
    claims = jwt.get_unverified_claims(valid_access)
    assert claims["type"] == "access"
    client.cookies.set("erp_access", client.cookies.get("erp_refresh"))
    assert client.get("/auth/browser/me").status_code == 401


def test_browser_mfa_challenge_never_exposes_bearer_tokens(browser_client, monkeypatch):
    client, _, _ = browser_client
    from app.mfa import totp_at

    clock = [1790000100.0]
    monkeypatch.setattr("app.mfa.time.time", lambda: clock[0])
    csrf = get_csrf(client)
    assert login(client, csrf).status_code == 200
    started = client.post(
        "/auth/mfa/setup", headers=headers(csrf),
        json={"current_password": "first-test-password"},
    )
    assert started.status_code == 200, started.text
    secret = started.json()["secret"]
    enabled = client.post(
        "/auth/mfa/confirm", headers=headers(csrf),
        json={"code": totp_at(secret, int(clock[0] // 30))},
    )
    assert enabled.status_code == 200, enabled.text

    challenge = login(client, csrf)
    assert challenge.status_code == 200, challenge.text
    data = challenge.json()
    assert data["mfa_required"] is True
    assert "access_token" not in data and "refresh_token" not in data
    clock[0] += 30
    verified = client.post(
        "/auth/browser/mfa/verify-login", headers=headers(csrf),
        json={
            "challenge_token": data["challenge_token"],
            "code": totp_at(secret, int(clock[0] // 30)),
        },
    )
    assert verified.status_code == 200, verified.text
    assert set(verified.json()) == {"role", "must_change_password"}
    assert client.get("/auth/browser/me").status_code == 200
