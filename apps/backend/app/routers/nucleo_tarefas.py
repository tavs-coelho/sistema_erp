"""Administrative task workflow for tenant-owned protocols.

Creator or assignee may view a task, admin sees all in tenant.
Only the assignee or admin may advance its state; final states are terminal.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Literal

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, get_tenant_id, require_roles
from ..models import Department, MunicipalTask, Protocolo, RoleEnum, User, utc_now

router = APIRouter(prefix="/nucleo/tarefas", tags=["nucleo-tarefas"])
CREATORS = (RoleEnum.admin, RoleEnum.accountant, RoleEnum.procurement)
TRANSITIONS = {
    "aberta": {"em_andamento", "concluida", "cancelada"},
    "em_andamento": {"concluida", "cancelada"},
    "concluida": set(),
    "cancelada": set(),
}


class TaskCreate(BaseModel):
    protocol_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=220)
    description: str = Field(default="", max_length=4000)
    assigned_user_id: int | None = Field(default=None, gt=0)
    department_id: int | None = Field(default=None, gt=0)
    priority: Literal["normal", "alta", "urgente"] = "normal"
    due_date: date | None = None


class TaskState(BaseModel):
    status: Literal["em_andamento", "concluida", "cancelada"]


class TaskOut(BaseModel):
    id: int
    tenant_id: int
    protocol_id: int
    title: str
    description: str
    assigned_user_id: int | None
    department_id: int | None
    created_by: int
    priority: str
    status: str
    due_date: date | None
    completed_at: object | None
    model_config = ConfigDict(from_attributes=True)


def _owner(db: Session, tenant: int, task_id: int, current: User, lock=False):
    q = db.query(MunicipalTask).filter(MunicipalTask.id == task_id,
                                      MunicipalTask.tenant_id == tenant)
    if current.role != RoleEnum.admin:
        q = q.filter(or_(MunicipalTask.assigned_user_id == current.id,
                         MunicipalTask.created_by == current.id))
    obj = q.with_for_update().first() if lock else q.first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return obj


def _tenant_user(db: Session, tenant: int, user_id: int) -> User:
    q = db.query(User).filter(User.id == user_id, User.active.is_(True))
    q = q.filter(
        or_(User.tenant_id == 1, User.tenant_id.is_(None))
        if tenant == 1 else User.tenant_id == tenant
    )
    person = q.first()
    if not person:
        raise HTTPException(status_code=404, detail="Responsável não localizado na entidade")
    return person


@router.get("/usuarios")
def eligible_users(db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
                   _: User = Depends(require_roles(*CREATORS))):
    q = db.query(User).filter(User.active.is_(True))
    q = q.filter(or_(User.tenant_id == 1, User.tenant_id.is_(None))
                 if tenant == 1 else User.tenant_id == tenant)
    return [{"id": item.id, "full_name": item.full_name} for item in q.order_by(User.full_name).limit(300).all()]


@router.get("", response_model=list[TaskOut])
def list_tasks(
    status: Literal["aberta", "em_andamento", "concluida", "cancelada"] | None = None,
    due_before: date | None = None,
    db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
    current: User = Depends(get_current_user),
):
    q = db.query(MunicipalTask).filter(MunicipalTask.tenant_id == tenant)
    if current.role != RoleEnum.admin:
        q = q.filter(or_(MunicipalTask.assigned_user_id == current.id,
                         MunicipalTask.created_by == current.id))
    if status:
        q = q.filter(MunicipalTask.status == status)
    if due_before:
        q = q.filter(MunicipalTask.due_date <= due_before)
    return q.order_by(MunicipalTask.id.desc()).limit(300).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db),
             tenant: int = Depends(get_tenant_id),
             current: User = Depends(get_current_user)):
    return _owner(db, tenant, task_id, current)


@router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db),
                tenant: int = Depends(get_tenant_id),
                current: User = Depends(require_roles(*CREATORS))):
    protocol = db.query(Protocolo).filter(Protocolo.id == payload.protocol_id,
                                         Protocolo.tenant_id == tenant).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    if protocol.status == "arquivado":
        raise HTTPException(status_code=409, detail="Protocolo arquivado")
    if payload.assigned_user_id:
        _tenant_user(db, tenant, payload.assigned_user_id)
    if payload.department_id and not db.query(Department).filter(
        Department.id == payload.department_id, Department.tenant_id == tenant,
        Department.active.is_(True),
    ).first():
        raise HTTPException(status_code=404, detail="Secretaria não encontrada")
    task = MunicipalTask(**payload.model_dump(), tenant_id=tenant, created_by=current.id)
    db.add(task)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="municipal_tasks",
                entity_id=str(task.id), after_data={"tenant_id": tenant, "protocol_id": task.protocol_id,
                                                    "assignee": task.assigned_user_id})
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/status", response_model=TaskOut)
def change_state(task_id: int, payload: TaskState, db: Session = Depends(get_db),
                 tenant: int = Depends(get_tenant_id),
                 current: User = Depends(get_current_user)):
    task = _owner(db, tenant, task_id, current, lock=True)
    if current.role != RoleEnum.admin and task.assigned_user_id != current.id:
        raise HTTPException(status_code=403, detail="Somente responsável ou administrador pode avançar")
    old = task.status
    if payload.status not in TRANSITIONS.get(old, set()):
        raise HTTPException(status_code=409, detail="Transição de estado não permitida")
    task.status = payload.status
    if payload.status == "concluida":
        task.completed_at = utc_now()
    write_audit(db, user_id=current.id, action="transition", entity="municipal_tasks",
                entity_id=str(task.id), before_data={"status": old},
                after_data={"tenant_id": tenant, "status": payload.status})
    db.commit()
    db.refresh(task)
    return task
