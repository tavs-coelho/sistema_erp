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


def test_login_and_refresh_flow():
    login = client.post("/auth/login", json={"username": "admin1", "password": "demo123"})
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"]
    refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200


def test_public_transparency_listing():
    response = client.get("/public/commitments?page=1&size=5")
    assert response.status_code == 200
    assert response.json()["total"] >= 12
