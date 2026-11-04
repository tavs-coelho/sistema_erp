"""Lotação de usuários em unidades municipais, sem elevação de papéis globais."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, get_tenant_id, require_roles
from ..models import MunicipalAssignment, MunicipalUnit, RoleEnum, User

router = APIRouter(prefix="/nucleo/lotacoes", tags=["nucleo-lotacoes"])


class AssignmentCreate(BaseModel):
    user_id: int = Field(gt=0)
    unit_id: int = Field(gt=0)


class AssignmentOut(BaseModel):
    id: int
    user_id: int
    unit_id: int
    active: bool
    model_config = ConfigDict(from_attributes=True)


class UserChoice(BaseModel):
    id: int
    username: str
    full_name: str
    role: RoleEnum
    model_config = ConfigDict(from_attributes=True)


def _user_in_tenant(db: Session, user_id: int, tenant: int) -> User:
    q = db.query(User).filter(User.id == user_id, User.active.is_(True))
    q = q.filter(
        or_(User.tenant_id == 1, User.tenant_id.is_(None))
        if tenant == 1 else User.tenant_id == tenant
    )
    user = q.first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado nesta entidade")
    return user


def _owned(db: Session, assignment_id: int, tenant: int):
    item = db.query(MunicipalAssignment).filter(
        MunicipalAssignment.id == assignment_id, MunicipalAssignment.tenant_id == tenant,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Lotação não encontrada")
    return item


@router.get("/usuarios", response_model=list[UserChoice])
def eligible_users(db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
                   _: User = Depends(require_roles(RoleEnum.admin))):
    q = db.query(User).filter(User.active.is_(True))
    q = q.filter(or_(User.tenant_id == 1, User.tenant_id.is_(None))
                 if tenant == 1 else User.tenant_id == tenant)
    return q.order_by(User.full_name).limit(300).all()


@router.get("", response_model=list[AssignmentOut])
def list_assignments(db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
                     _: User = Depends(require_roles(RoleEnum.admin))):
    return db.query(MunicipalAssignment).filter(
        MunicipalAssignment.tenant_id == tenant,
        MunicipalAssignment.active.is_(True),
    ).order_by(MunicipalAssignment.id).limit(500).all()


@router.get("/minhas", response_model=list[AssignmentOut])
def my_assignments(db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
                   current: User = Depends(get_current_user)):
    return db.query(MunicipalAssignment).filter(
        MunicipalAssignment.tenant_id == tenant, MunicipalAssignment.user_id == current.id,
        MunicipalAssignment.active.is_(True),
    ).all()


@router.post("", response_model=AssignmentOut, status_code=201)
def assign(payload: AssignmentCreate, db: Session = Depends(get_db),
           tenant: int = Depends(get_tenant_id),
           current: User = Depends(require_roles(RoleEnum.admin))):
    _user_in_tenant(db, payload.user_id, tenant)
    unit = db.query(MunicipalUnit).filter(
        MunicipalUnit.id == payload.unit_id, MunicipalUnit.tenant_id == tenant,
        MunicipalUnit.active.is_(True),
    ).first()
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidade não encontrada nesta entidade")
    existing = db.query(MunicipalAssignment).filter(
        MunicipalAssignment.tenant_id == tenant,
        MunicipalAssignment.user_id == payload.user_id,
        MunicipalAssignment.unit_id == payload.unit_id,
    ).first()
    if existing and existing.active:
        raise HTTPException(status_code=409, detail="Lotação já existe")
    item = existing or MunicipalAssignment(
        tenant_id=tenant, user_id=payload.user_id, unit_id=payload.unit_id,
    )
    item.active = True
    db.add(item)
    db.flush()
    write_audit(db, user_id=current.id, action="assign", entity="municipal_assignments",
                entity_id=str(item.id), after_data={"tenant_id": tenant, "user_id": item.user_id,
                                                     "unit_id": item.unit_id})
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{assignment_id}")
def revoke_assignment(assignment_id: int, db: Session = Depends(get_db),
                      tenant: int = Depends(get_tenant_id),
                      current: User = Depends(require_roles(RoleEnum.admin))):
    item = _owned(db, assignment_id, tenant)
    item.active = False
    write_audit(db, user_id=current.id, action="revoke", entity="municipal_assignments",
                entity_id=str(item.id), after_data={"tenant_id": tenant, "active": False})
    db.commit()
    return {"message": "Lotação encerrada"}
