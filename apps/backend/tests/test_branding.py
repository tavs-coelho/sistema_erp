import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_data


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)
    db.close()


client = TestClient(app)


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_get_branding_public():
    """GET /branding requires no authentication."""
    r = client.get("/branding")
    assert r.status_code == 200
    data = r.json()
    assert "org_name" in data
    assert "primary_color" in data
    assert "secondary_color" in data
    assert "accent_color" in data
    assert "app_title" in data


def test_update_branding_admin():
    """Admin can update branding settings."""
    headers = auth_headers("admin1")
    payload = {
        "org_name": "Prefeitura de Teste",
        "primary_color": "#e53e3e",
        "secondary_color": "#1a202c",
        "accent_color": "#3182ce",
        "app_title": "ERP Teste",
    }
    r = client.put("/branding", json=payload, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["org_name"] == "Prefeitura de Teste"
    assert data["primary_color"] == "#e53e3e"
    assert data["app_title"] == "ERP Teste"


def test_update_branding_non_admin_rejected():
    """Non-admin users must not be able to update branding."""
    headers = auth_headers("accountant1")
    r = client.put("/branding", json={"org_name": "Hack"}, headers=headers)
    assert r.status_code == 403


def test_update_branding_invalid_color():
    """Invalid hex colour values are rejected with 422."""
    headers = auth_headers("admin1")
    r = client.put("/branding", json={"primary_color": "not-a-color"}, headers=headers)
    assert r.status_code == 422


def test_update_branding_partial():
    """Only provided fields are changed; others stay as-is."""
    headers = auth_headers("admin1")
    # Set a known state first
    client.put("/branding", json={"org_name": "Município A", "app_title": "ERP A"}, headers=headers)
    # Partial update — only org_name
    r = client.put("/branding", json={"org_name": "Município B"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["org_name"] == "Município B"
    assert data["app_title"] == "ERP A"  # unchanged


def test_get_branding_reflects_updates():
    """Public GET returns the most recently saved values."""
    headers = auth_headers("admin1")
    client.put("/branding", json={"org_name": "Confirmado Via GET"}, headers=headers)
    r = client.get("/branding")
    assert r.status_code == 200
    assert r.json()["org_name"] == "Confirmado Via GET"
