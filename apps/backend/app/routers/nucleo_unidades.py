"""Cadastro de unidades administrativas por ente federativo."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, get_tenant_id, require_roles
from ..models import Department, MunicipalUnit, RoleEnum, User

router = APIRouter(prefix="/nucleo/unidades", tags=["nucleo-unidades"])


class UnitCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=180)
    department_id: int = Field(gt=0)
    address: str = Field(default="", max_length=350)


class UnitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    department_id: int | None = Field(default=None, gt=0)
    address: str | None = Field(default=None, max_length=350)
    active: bool | None = None


class UnitOut(BaseModel):
    id: int
    tenant_id: int
    code: str
    name: str
    department_id: int
    address: str
    active: bool
    model_config = ConfigDict(from_attributes=True)


def _department(db: Session, tenant: int, department_id: int):
    item = db.query(Department).filter(
        Department.tenant_id == tenant, Department.id == department_id,
        Department.active.is_(True),
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Departamento não localizado nesta entidade")


def _unit(db: Session, tenant: int, unit_id: int):
    item = db.query(MunicipalUnit).filter(
        MunicipalUnit.tenant_id == tenant, MunicipalUnit.id == unit_id,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Unidade não localizada")
    return item


@router.get("", response_model=list[UnitOut])
def list_units(
    search: str = Query("", max_length=100),
    active: bool | None = None,
    db: Session = Depends(get_db),
    tenant: int = Depends(get_tenant_id),
    _: User = Depends(get_current_user),
):
    query = db.query(MunicipalUnit).filter(MunicipalUnit.tenant_id == tenant)
    if active is not None:
        query = query.filter(MunicipalUnit.active == active)
    if search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(MunicipalUnit.name.ilike(pattern), MunicipalUnit.code.ilike(pattern)))
    return query.order_by(MunicipalUnit.name).limit(300).all()


@router.get("/{unit_id}", response_model=UnitOut)
def get_unit(unit_id: int, db: Session = Depends(get_db),
             tenant: int = Depends(get_tenant_id), _: User = Depends(get_current_user)):
    return _unit(db, tenant, unit_id)


@router.post("", response_model=UnitOut, status_code=201)
def create_unit(payload: UnitCreate, db: Session = Depends(get_db),
                tenant: int = Depends(get_tenant_id),
                current: User = Depends(require_roles(RoleEnum.admin))):
    _department(db, tenant, payload.department_id)
    code = payload.code.strip().upper()
    if db.query(MunicipalUnit).filter(
        MunicipalUnit.tenant_id == tenant, MunicipalUnit.code == code
    ).first():
        raise HTTPException(status_code=409, detail="Código já cadastrado nesta entidade")
    obj = MunicipalUnit(tenant_id=tenant, code=code,
                        name=payload.name.strip(), address=payload.address.strip(),
                        department_id=payload.department_id)
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="municipal_units",
                entity_id=str(obj.id), after_data={"tenant_id": tenant, "code": code})
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{unit_id}", response_model=UnitOut)
def update_unit(unit_id: int, payload: UnitUpdate, db: Session = Depends(get_db),
                tenant: int = Depends(get_tenant_id),
                current: User = Depends(require_roles(RoleEnum.admin))):
    item = _unit(db, tenant, unit_id)
    if payload.department_id is not None:
        _department(db, tenant, payload.department_id)
    before = {"name": item.name, "active": item.active}
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(item, key, value.strip() if isinstance(value, str) else value)
    write_audit(db, user_id=current.id, action="update", entity="municipal_units",
                entity_id=str(item.id), before_data=before,
                after_data={"tenant_id": tenant, "updated_fields": sorted(payload.model_fields_set)})
    db.commit()
    db.refresh(item)
    return item
