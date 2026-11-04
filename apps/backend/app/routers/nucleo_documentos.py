"""Municipal GED with ownership, version history and secure content downloads.

Documents are private to tenant. Restrito is visible to creator or admin only.
Actual file bytes are only served after database authorization checks.
"""
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import settings
from ..db import get_db
from ..deps import get_current_user, get_tenant_id, require_roles
from ..models import MunicipalDocument, MunicipalDocumentVersion, Protocolo, RoleEnum, User

router = APIRouter(prefix="/nucleo/documentos", tags=["nucleo-ged"])
EDITORS = (RoleEnum.admin, RoleEnum.accountant, RoleEnum.procurement, RoleEnum.hr, RoleEnum.patrimony)
MAX_SIZE = 8 * 1024 * 1024
MIMES = {"application/pdf", "image/png", "image/jpeg", "text/plain"}


class DocumentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=3, max_length=220)
    classification: Literal["publico", "interno", "restrito"] = "interno"
    protocol_id: int | None = Field(default=None, gt=0)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=220)
    status: Literal["ativo", "arquivado"] | None = None


class DocumentOut(BaseModel):
    id: int
    code: str
    title: str
    classification: str
    status: str
    protocol_id: int | None
    latest_version: int
    created_by: int
    model_config = ConfigDict(from_attributes=True)


class VersionOut(BaseModel):
    id: int
    document_id: int
    version: int
    original_name: str
    mime_type: str
    content_sha256: str
    size_bytes: int
    model_config = ConfigDict(from_attributes=True)


def _authorized(item: MunicipalDocument, current: User) -> bool:
    if item.classification == "restrito":
        return current.role == RoleEnum.admin or item.created_by == current.id
    if item.classification == "publico":
        return True
    return current.role not in {RoleEnum.employee, RoleEnum.read_only}


def _owned(db: Session, tenant: int, doc_id: int, current: User):
    item = db.query(MunicipalDocument).filter(
        MunicipalDocument.id == doc_id, MunicipalDocument.tenant_id == tenant
    ).first()
    if not item or not _authorized(item, current):
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return item


def _verify_bytes(mime: str, data: bytes) -> None:
    if mime not in MIMES:
        raise HTTPException(status_code=415, detail="Formato de arquivo não permitido")
    if not data:
        raise HTTPException(status_code=422, detail="Arquivo vazio")
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Limite de arquivo: 8 MB")
    valid = (
        (mime == "application/pdf" and data.startswith(b"%PDF-"))
        or (mime == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
        or (mime == "image/jpeg" and data.startswith(b"\xff\xd8\xff"))
        or (mime == "text/plain" and _is_utf8(data))
    )
    if not valid:
        raise HTTPException(status_code=422, detail="Conteúdo não corresponde ao tipo de arquivo")


def _is_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
    current: User = Depends(get_current_user),
):
    q = db.query(MunicipalDocument).filter(MunicipalDocument.tenant_id == tenant)
    if current.role in {RoleEnum.employee, RoleEnum.read_only}:
        q = q.filter(MunicipalDocument.classification == "publico")
    elif current.role != RoleEnum.admin:
        q = q.filter(or_(
            MunicipalDocument.classification != "restrito",
            MunicipalDocument.created_by == current.id,
        ))
    return q.order_by(MunicipalDocument.id.desc()).limit(300).all()


@router.post("", response_model=DocumentOut, status_code=201)
def create_document(
    payload: DocumentCreate, db: Session = Depends(get_db),
    tenant: int = Depends(get_tenant_id),
    current: User = Depends(require_roles(*EDITORS)),
):
    if payload.protocol_id is not None and not db.query(Protocolo).filter(
        Protocolo.id == payload.protocol_id, Protocolo.tenant_id == tenant
    ).first():
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    code = payload.code.strip().upper()
    if db.query(MunicipalDocument).filter(
        MunicipalDocument.tenant_id == tenant, MunicipalDocument.code == code
    ).first():
        raise HTTPException(status_code=409, detail="Código já usado nesta entidade")
    obj = MunicipalDocument(tenant_id=tenant, code=code, title=payload.title.strip(),
                            classification=payload.classification, protocol_id=payload.protocol_id,
                            created_by=current.id)
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="municipal_documents",
                entity_id=str(obj.id), after_data={"tenant_id": tenant, "classification": obj.classification})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db),
                 tenant: int = Depends(get_tenant_id),
                 current: User = Depends(get_current_user)):
    return _owned(db, tenant, doc_id, current)


@router.patch("/{doc_id}", response_model=DocumentOut)
def edit_document(doc_id: int, payload: DocumentUpdate, db: Session = Depends(get_db),
                  tenant: int = Depends(get_tenant_id),
                  current: User = Depends(require_roles(*EDITORS))):
    obj = _owned(db, tenant, doc_id, current)
    if current.role != RoleEnum.admin and obj.created_by != current.id:
        raise HTTPException(status_code=403, detail="Somente criador ou administrador pode editar")
    changes = payload.model_dump(exclude_none=True)
    for key, value in changes.items():
        setattr(obj, key, value.strip() if isinstance(value, str) else value)
    write_audit(db, user_id=current.id, action="update", entity="municipal_documents",
                entity_id=str(obj.id), after_data={"tenant_id": tenant, "fields": sorted(changes)})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{doc_id}/versions", response_model=list[VersionOut])
def list_versions(doc_id: int, db: Session = Depends(get_db),
                  tenant: int = Depends(get_tenant_id),
                  current: User = Depends(get_current_user)):
    _owned(db, tenant, doc_id, current)
    return db.query(MunicipalDocumentVersion).filter(
        MunicipalDocumentVersion.tenant_id == tenant,
        MunicipalDocumentVersion.document_id == doc_id,
    ).order_by(MunicipalDocumentVersion.version.desc()).all()


@router.post("/{doc_id}/versions", response_model=VersionOut, status_code=201)
def upload_version(
    doc_id: int, file: UploadFile = File(...),
    db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
    current: User = Depends(require_roles(*EDITORS)),
):
    item = db.query(MunicipalDocument).filter(
        MunicipalDocument.id == doc_id, MunicipalDocument.tenant_id == tenant,
    ).with_for_update().first()
    if not item or not _authorized(item, current):
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if current.role != RoleEnum.admin and item.created_by != current.id:
        raise HTTPException(status_code=403, detail="Somente criador ou administrador pode versionar")
    if item.status != "ativo":
        raise HTTPException(status_code=409, detail="Documento arquivado")
    data = file.file.read(MAX_SIZE + 1)
    mime = file.content_type or ""
    _verify_bytes(mime, data)
    original = (Path(file.filename or "arquivo").name).replace("\x00", "")[:180] or "arquivo"
    next_version = item.latest_version + 1
    key = f"nucleo/{tenant}/{doc_id}/{uuid4().hex}"
    root = Path(settings.upload_dir).resolve()
    path = root / key
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
    try:
        version = MunicipalDocumentVersion(
            document_id=doc_id, tenant_id=tenant, version=next_version,
            original_name=original, storage_key=key, mime_type=mime,
            content_sha256=sha256(data).hexdigest(), size_bytes=len(data), uploaded_by=current.id,
        )
        db.add(version)
        item.latest_version = next_version
        db.flush()
        write_audit(db, user_id=current.id, action="version", entity="municipal_documents",
                    entity_id=str(doc_id), after_data={"tenant_id": tenant, "version": next_version,
                                                       "sha256": version.content_sha256})
        db.commit()
        db.refresh(version)
        return version
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise


@router.get("/{doc_id}/versions/{version_id}/download")
def download_version(doc_id: int, version_id: int,
                     db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
                     current: User = Depends(get_current_user)):
    _owned(db, tenant, doc_id, current)
    version = db.query(MunicipalDocumentVersion).filter(
        MunicipalDocumentVersion.id == version_id,
        MunicipalDocumentVersion.document_id == doc_id,
        MunicipalDocumentVersion.tenant_id == tenant,
    ).first()
    if version is None:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    root = Path(settings.upload_dir).resolve()
    path = (root / version.storage_key).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo indisponível")
    return FileResponse(path, media_type=version.mime_type,
                        filename=version.original_name,
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
