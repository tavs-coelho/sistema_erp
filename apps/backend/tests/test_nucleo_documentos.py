"""GED: immutable versions, tenant isolation, classification and real file content."""
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.deps import get_tenant_id
from app.main import app
from app.models import MunicipalDocument, MunicipalDocumentVersion, RoleEnum, TenantBranding, User
from app.security import create_access_token, hash_password


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as db:
        db.add_all([
            TenantBranding(id=1, org_name="Entidade 1"),
            TenantBranding(id=2, org_name="Entidade 2"),
            User(id=151, username="ged-admin-151", full_name="Admin A",
                 email="ged151@example.org", hashed_password=hash_password("test"),
                 tenant_id=1, role=RoleEnum.admin),
            User(id=152, username="ged-admin-152", full_name="Admin B",
                 email="ged152@example.org", hashed_password=hash_password("test"),
                 tenant_id=2, role=RoleEnum.admin),
            User(id=153, username="ged-reader-153", full_name="Leitor",
                 email="ged153@example.org", hashed_password=hash_password("test"),
                 tenant_id=1, role=RoleEnum.read_only),
        ])
        db.commit()
    def db_override():
        with maker() as db:
            yield db
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_tenant_id] = lambda: 1
    client = TestClient(app)
    try:
        yield client, maker, lambda tenant: app.dependency_overrides.__setitem__(get_tenant_id, lambda: tenant)
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_tenant_id, None)
        engine.dispose()


def auth(uid, role="admin"):
    return {"Authorization": f"Bearer {create_access_token(uid, role)}"}


def test_document_versions_audit_checksum_and_safe_content(env):
    client, maker, _ = env
    created = client.post("/nucleo/documentos", headers=auth(151),
                          json={"code": "ADM-001", "title": "Memorando de teste",
                                "classification": "interno"})
    assert created.status_code == 201, created.text
    did = created.json()["id"]
    pdf = b"%PDF-1.4\n1 0 obj\nendobj\n%%EOF"
    v1 = client.post(f"/nucleo/documentos/{did}/versions", headers=auth(151),
                     files={"file": ("memorando.pdf", pdf, "application/pdf")})
    assert v1.status_code == 201, v1.text
    assert v1.json()["version"] == 1
    assert v1.json()["content_sha256"] == sha256(pdf).hexdigest()
    v2 = client.post(f"/nucleo/documentos/{did}/versions", headers=auth(151),
                     files={"file": ("revisao.txt", b"Versao 2", "text/plain")})
    assert v2.status_code == 201 and v2.json()["version"] == 2
    versions = client.get(f"/nucleo/documentos/{did}/versions", headers=auth(151))
    assert [v["version"] for v in versions.json()] == [2, 1]
    downloaded = client.get(f"/nucleo/documentos/{did}/versions/{v1.json()['id']}/download",
                            headers=auth(151))
    assert downloaded.status_code == 200 and downloaded.content == pdf
    with maker() as db:
        assert db.get(MunicipalDocument, did).latest_version == 2
        assert db.query(MunicipalDocumentVersion).filter(
            MunicipalDocumentVersion.document_id == did
        ).count() == 2
    assert client.post(f"/nucleo/documentos/{did}/versions", headers=auth(151),
                       files={"file": ("falso.pdf", b"not pdf", "application/pdf")}).status_code == 422
    assert client.patch(f"/nucleo/documentos/{did}", headers=auth(151),
                        json={"status": "arquivado"}).status_code == 200
    assert client.post(f"/nucleo/documentos/{did}/versions", headers=auth(151),
                       files={"file": ("again.txt", b"text", "text/plain")}).status_code == 409


def test_restricted_document_visibility_and_cross_tenant_download(env):
    client, _, switch = env
    restricted = client.post("/nucleo/documentos", headers=auth(151), json={
        "code": "RESTRITO", "title": "Processo reservado",
        "classification": "restrito",
    })
    assert restricted.status_code == 201
    did = restricted.json()["id"]
    version = client.post(f"/nucleo/documentos/{did}/versions", headers=auth(151),
                          files={"file": ("restrito.txt", b"teste ficticio", "text/plain")})
    assert version.status_code == 201
    vid = version.json()["id"]
    assert client.get("/nucleo/documentos", headers=auth(153, "read_only")).json() == []
    assert client.get(f"/nucleo/documentos/{did}", headers=auth(153, "read_only")).status_code == 404
    switch(2)
    assert client.get("/nucleo/documentos", headers=auth(152)).json() == []
    assert client.get(f"/nucleo/documentos/{did}", headers=auth(152)).status_code == 404
    assert client.get(f"/nucleo/documentos/{did}/versions/{vid}/download",
                      headers=auth(152)).status_code == 404
    assert client.post(f"/nucleo/documentos/{did}/versions", headers=auth(152),
                       files={"file": ("attack.txt", b"wrong tenant", "text/plain")}).status_code == 404
