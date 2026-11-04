"""Operational response hardening tests with no production database."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.operational import ApiSecurityHeadersMiddleware, router


def test_security_headers_request_id_and_sensitive_cache_control():
    app = FastAPI()
    app.add_middleware(ApiSecurityHeadersMiddleware)
    @app.get("/core/test")
    def sensitive():
        return {"ok": True}
    with TestClient(app) as client:
        response = client.get("/core/test", headers={"X-Request-ID": "Request_123"})
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == "Request_123"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        bad = client.get("/core/test", headers={"X-Request-ID": "x" * 70})
        assert len(bad.headers["X-Request-ID"]) == 32


def test_health_live_responds_without_database():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "alive"}


def test_health_ready_fails_closed_on_database_exception(monkeypatch):
    from app import operational
    class BadSession:
        def __enter__(self):
            raise RuntimeError("database down")
        def __exit__(self, *args):
            return False
    monkeypatch.setattr(operational, "SessionLocal", BadSession)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
