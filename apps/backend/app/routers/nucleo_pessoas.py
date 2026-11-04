"""Entity-restricted directory of municipal parties and supplier contacts.

This module deliberately does not synchronize the legacy global vendors table
until financial/procurement tables have tenant-safe foreign keys.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_tenant_id, require_roles
from ..models import MunicipalParty, RoleEnum, User

router = APIRouter(prefix="/nucleo/pessoas", tags=["nucleo-pessoas"])
MANAGERS = (RoleEnum.admin, RoleEnum.procurement, RoleEnum.accountant)


class PartyCreate(BaseModel):
    kind: Literal["pessoa", "fornecedor"]
    name: str = Field(min_length=2, max_length=180)
    document: str | None = Field(default=None, max_length=18)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)


class PartyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    active: bool | None = None


class PartyOut(BaseModel):
    id: int
    kind: str
    name: str
    document: str | None
    email: str | None
    phone: str | None
    active: bool
    model_config = ConfigDict(from_attributes=True)


def normalize_document(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    if any(ch not in "0123456789.-/" for ch in value):
        raise HTTPException(status_code=422, detail="Documento deve conter apenas dígitos e separadores")
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) not in {11, 14}:
        raise HTTPException(status_code=422, detail="CPF/CNPJ deve conter 11 ou 14 dígitos")
    return digits


def _owned(db: Session, tenant: int, party_id: int):
    item = db.query(MunicipalParty).filter(
        MunicipalParty.id == party_id, MunicipalParty.tenant_id == tenant,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    return item


@router.get("", response_model=list[PartyOut])
def list_parties(
    kind: Literal["pessoa", "fornecedor"] | None = None,
    search: str = Query("", max_length=100),
    db: Session = Depends(get_db),
    tenant: int = Depends(get_tenant_id),
    _: User = Depends(require_roles(*MANAGERS)),
):
    query = db.query(MunicipalParty).filter(MunicipalParty.tenant_id == tenant)
    if kind:
        query = query.filter(MunicipalParty.kind == kind)
    if search.strip():
        query = query.filter(MunicipalParty.name.ilike(f"%{search.strip()}%"))
    return query.order_by(MunicipalParty.name).limit(300).all()


@router.get("/{party_id}", response_model=PartyOut)
def get_party(party_id: int, db: Session = Depends(get_db),
              tenant: int = Depends(get_tenant_id),
              _: User = Depends(require_roles(*MANAGERS))):
    return _owned(db, tenant, party_id)


@router.post("", response_model=PartyOut, status_code=201)
def create_party(payload: PartyCreate, db: Session = Depends(get_db),
                 tenant: int = Depends(get_tenant_id),
                 current: User = Depends(require_roles(*MANAGERS))):
    document = normalize_document(payload.document)
    if document and db.query(MunicipalParty).filter(
        MunicipalParty.tenant_id == tenant, MunicipalParty.document == document
    ).first():
        raise HTTPException(status_code=409, detail="Documento já cadastrado nesta entidade")
    obj = MunicipalParty(
        tenant_id=tenant, kind=payload.kind, name=payload.name.strip(),
        document=document, email=str(payload.email) if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
    )
    db.add(obj)
    db.flush()
    # Do NOT put CPF/CNPJ, email or phone into the audit trail.
    write_audit(db, user_id=current.id, action="create", entity="municipal_parties",
                entity_id=str(obj.id), after_data={"tenant_id": tenant, "kind": obj.kind})
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{party_id}", response_model=PartyOut)
def update_party(party_id: int, payload: PartyUpdate, db: Session = Depends(get_db),
                 tenant: int = Depends(get_tenant_id),
                 current: User = Depends(require_roles(*MANAGERS))):
    obj = _owned(db, tenant, party_id)
    changed = payload.model_dump(exclude_unset=True)
    for key, value in changed.items():
        setattr(obj, key, str(value).strip() if value is not None and key in {"name", "email", "phone"} else value)
    write_audit(db, user_id=current.id, action="update", entity="municipal_parties",
                entity_id=str(obj.id),
                after_data={"tenant_id": tenant, "fields": sorted(changed)})
    db.commit()
    db.refresh(obj)
    return obj
