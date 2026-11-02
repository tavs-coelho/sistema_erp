"""Middleware regression tests: unknown tenant hosts must not fall back to tenant 1."""
from fastapi.testclient import TestClient

from app.main import app


def test_unknown_subdomain_rejected(monkeypatch):
    monkeypatch.setattr("app.middleware._lookup_tenant", lambda subdomain: None)
    client = TestClient(app)
    response = client.get("/", headers={"Host": "nonexistent.erp.app"})
    assert response.status_code == 404


def test_known_subdomain_is_allowed(monkeypatch):
    monkeypatch.setattr("app.middleware._lookup_tenant", lambda subdomain: 2)
    client = TestClient(app)
    response = client.get("/", headers={"Host": "cidade-dois.erp.app"})
    assert response.status_code == 200


def test_localhost_remains_default_tenant(monkeypatch):
    def should_not_lookup(subdomain):
        raise AssertionError("localhost should not query tenant directory")

    monkeypatch.setattr("app.middleware._lookup_tenant", should_not_lookup)
    client = TestClient(app)
    response = client.get("/", headers={"Host": "localhost:8000"})
    assert response.status_code == 200
