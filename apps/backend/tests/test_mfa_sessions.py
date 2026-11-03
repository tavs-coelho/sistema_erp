"""TOTP MFA / revocable JWT regression tests using isolated in-memory SQLite."""
from datetime import datetime

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.deps import get_tenant_id
from app.main import app
from app.mfa import totp_at, valid_totp_counter
from app.models import MfaRecoveryCode, RoleEnum, TenantBranding, User, UserMfa
from app.security import hash_password


@pytest.fixture
def mfa_client(monkeypatch):
    monkeypatch.setattr(settings, "mfa_encryption_key", Fernet.generate_key().decode("ascii"))
    moment = [1790000100.0]
    monkeypatch.setattr("app.mfa.time.time", lambda: moment[0])
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False, autoflush=False)
    with factory() as db:
        db.add_all([
            TenantBranding(id=1, subdomain="prefeitura-um"),
            TenantBranding(id=2, subdomain="prefeitura-dois"),
            User(id=15, username="admin-mfa", full_name="Admin MFA", email="admin-mfa@example.org",
                 role=RoleEnum.admin, hashed_password=hash_password("password-test-123"),
                 tenant_id=1, active=True, session_version=0),
            User(id=25, username="other-mfa", full_name="Other", email="other@example.org",
                 role=RoleEnum.admin, hashed_password=hash_password("password-test-other"),
                 tenant_id=2, active=True, session_version=0),
        ])
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = lambda: 1
    client = TestClient(app)
    try:
        yield client, factory, moment, lambda t: app.dependency_overrides.__setitem__(get_tenant_id, lambda: t)
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_tenant_id, None)
        engine.dispose()


def _login(client):
    return client.post("/auth/login", json={"username": "admin-mfa", "password": "password-test-123"})


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _enroll(client, moment):
    first = _login(client)
    assert first.status_code == 200
    old_tokens = first.json()
    started = client.post("/auth/mfa/setup", headers=_headers(old_tokens["access_token"]),
                          json={"current_password": "password-test-123"})
    assert started.status_code == 200
    secret = started.json()["secret"]
    assert started.json()["provisioning_uri"].startswith("otpauth://totp/")
    invalid = client.post("/auth/mfa/confirm", headers=_headers(old_tokens["access_token"]), json={"code": "INVALID"})
    assert invalid.status_code == 400
    valid = client.post("/auth/mfa/confirm", headers=_headers(old_tokens["access_token"]),
                        json={"code": totp_at(secret, int(moment[0] // 30))})
    assert valid.status_code == 200
    return secret, old_tokens, valid.json()["recovery_codes"]


def test_rfc6238_sha1_known_vector_and_replay():
    import base64
    secret = base64.b32encode(b"12345678901234567890").decode()
    assert totp_at(secret, 1) == "287082"  # RFC 6238 SHA1 vector, reduced to six digits
    assert valid_totp_counter(secret, "287082", now=59) == 1
    assert valid_totp_counter(secret, "287082", last_used=1, now=59) is None
    assert valid_totp_counter(secret, "12x456", now=59) is None


def test_mfa_enrollment_requires_password_and_encrypted_secret(mfa_client):
    client, factory, moment, _ = mfa_client
    token = _login(client).json()["access_token"]
    rejected = client.post("/auth/mfa/setup", headers=_headers(token), json={"current_password": "wrong"})
    assert rejected.status_code == 401
    secret, old_tokens, codes = _enroll(client, moment)
    assert len(codes) == 10 and len(set(codes)) == 10
    with factory() as db:
        credential = db.get(UserMfa, 15)
        assert credential.enabled and secret not in credential.encrypted_secret
        assert db.query(MfaRecoveryCode).filter(MfaRecoveryCode.user_id == 15).count() == 10
        assert all(c not in str(db.query(MfaRecoveryCode).all()) for c in codes)
    assert client.get("/auth/me", headers=_headers(old_tokens["access_token"])).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": old_tokens["refresh_token"]}).status_code == 401


def test_second_factor_enforced_and_challenge_one_time(mfa_client):
    client, _, moment, _ = mfa_client
    secret, _, _ = _enroll(client, moment)
    challenge = _login(client).json()
    assert challenge["mfa_required"] and "access_token" not in challenge
    wrong = client.post("/auth/mfa/verify-login", json={
        "challenge_token": challenge["challenge_token"], "code": "000000"})
    assert wrong.status_code == 401
    moment[0] += 30
    code = totp_at(secret, int(moment[0] // 30))
    verified = client.post("/auth/mfa/verify-login", json={
        "challenge_token": challenge["challenge_token"], "code": code})
    assert verified.status_code == 200
    tokens = verified.json()
    assert client.get("/auth/me", headers=_headers(tokens["access_token"])).status_code == 200
    assert client.post("/auth/mfa/verify-login", json={
        "challenge_token": challenge["challenge_token"], "code": code}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 200


def test_recovery_code_one_time_and_tenant_bound(mfa_client):
    client, factory, moment, set_tenant = mfa_client
    _, _, codes = _enroll(client, moment)
    challenge = _login(client).json()["challenge_token"]
    set_tenant(2)
    assert client.post("/auth/mfa/verify-login", json={
        "challenge_token": challenge, "code": codes[0]}).status_code == 401
    set_tenant(1)
    used = client.post("/auth/mfa/verify-login", json={
        "challenge_token": challenge, "code": codes[0]})
    assert used.status_code == 200
    with factory() as db:
        assert db.query(MfaRecoveryCode).filter(MfaRecoveryCode.user_id == 15).count() == 9
    another = _login(client).json()["challenge_token"]
    assert client.post("/auth/mfa/verify-login", json={
        "challenge_token": another, "code": codes[0]}).status_code == 401
    assert client.post("/auth/mfa/verify-login", json={
        "challenge_token": another, "code": codes[1]}).status_code == 200


def test_logout_revokes_all_tokens_and_disable_requires_both_factors(mfa_client):
    client, _, moment, _ = mfa_client
    secret, _, _ = _enroll(client, moment)
    challenge = _login(client).json()["challenge_token"]
    moment[0] += 30
    verified = client.post("/auth/mfa/verify-login", json={
        "challenge_token": challenge, "code": totp_at(secret, int(moment[0] // 30))}).json()
    token = verified["access_token"]
    refresh = verified["refresh_token"]
    bad = client.post("/auth/mfa/disable", headers=_headers(token),
                      json={"current_password": "wrong", "code": "000000"})
    assert bad.status_code == 401
    moment[0] += 30
    disabled = client.post("/auth/mfa/disable", headers=_headers(token), json={
        "current_password": "password-test-123", "code": totp_at(secret, int(moment[0] // 30))})
    assert disabled.status_code == 200
    assert client.get("/auth/me", headers=_headers(token)).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401
    new_login = _login(client)
    assert new_login.status_code == 200 and "access_token" in new_login.json()
    new_tokens = new_login.json()
    logout = client.post("/auth/logout", headers=_headers(new_tokens["access_token"]))
    assert logout.status_code == 200
    assert client.get("/auth/me", headers=_headers(new_tokens["access_token"])).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}).status_code == 401


def test_password_reset_revokes_existing_sessions(mfa_client):
    client, factory, _, _ = mfa_client
    prior = _login(client).json()
    reset = client.post("/auth/request-password-reset", json={"username": "admin-mfa"})
    assert reset.status_code == 200
    with factory() as db:
        from app.models import PasswordResetToken
        token = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == 15).first().token
    changed = client.post("/auth/reset-password", json={"token": token, "new_password": "fresh-password-test"})
    assert changed.status_code == 200
    assert client.get("/auth/me", headers=_headers(prior["access_token"])).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": prior["refresh_token"]}).status_code == 401


def test_mfa_secret_key_not_configured_fails_closed(mfa_client, monkeypatch):
    client, _, _, _ = mfa_client
    token = _login(client).json()["access_token"]
    monkeypatch.setattr(settings, "mfa_encryption_key", None)
    response = client.post("/auth/mfa/setup", headers=_headers(token),
                           json={"current_password": "password-test-123"})
    assert response.status_code == 503
