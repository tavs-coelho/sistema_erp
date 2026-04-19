from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import settings
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Attachment, AuditLog, Department, FiscalYear, RoleEnum, User
from ..schemas import DepartmentCreate, DepartmentOut, DepartmentUpdate, UserCreate, UserOut, UserUpdate
from ..security import hash_password

router = APIRouter(prefix="/core", tags=["core"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    active: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.read_only)),
):
    q = db.query(User)
    if active is not None:
        q = q.filter(User.active == active)
    return q.order_by(User.id).all()


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin))):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Nome de usuário já em uso")
    user = User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        role=payload.role,
        hashed_password=hash_password(payload.password),
        employee_id=payload.employee_id,
    )
    db.add(user)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="users", entity_id=str(user.id), after_data={"username": user.username})
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    before = {"role": user.role.value, "active": user.active}
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        user.email = payload.email
    if payload.role is not None:
        user.role = payload.role
    if payload.active is not None:
        user.active = payload.active
    write_audit(db, user_id=current.id, action="update", entity="users", entity_id=str(user.id), before_data=before, after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(user)
    return user


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(
    active: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Department)
    if active is not None:
        q = q.filter(Department.active == active)
    return q.order_by(Department.name).all()


@router.post("/departments", response_model=DepartmentOut)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin))):
    dep = Department(name=payload.name)
    db.add(dep)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="departments", entity_id=str(dep.id), after_data={"name": dep.name})
    db.commit()
    db.refresh(dep)
    return dep


@router.patch("/departments/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin)),
):
    dep = db.get(Department, department_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")
    before = {"name": dep.name, "active": dep.active}
    if payload.name is not None:
        dep.name = payload.name
    if payload.active is not None:
        dep.active = payload.active
    write_audit(db, user_id=current.id, action="update", entity="departments", entity_id=str(dep.id), before_data=before, after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(dep)
    return dep


@router.get("/fiscal-years")
def list_fiscal_years(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(FiscalYear).all()


@router.get("/audit-logs")
def list_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    action: str | None = None,
    entity: str | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.read_only)),
):
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        q = q.filter(AuditLog.action == action)
    if entity:
        q = q.filter(AuditLog.entity.ilike(f"%{entity}%"))
    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": items}


@router.post("/attachments")
def upload_attachment(
    entity_type: str,
    entity_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")
    safe_name = Path(file.filename).name
    if not safe_name:
        raise HTTPException(status_code=400, detail="Arquivo inválido")
    path = upload_dir / safe_name
    path.write_bytes(file.file.read())
    att = Attachment(entity_type=entity_type, entity_id=entity_id, file_name=safe_name, path=str(path))
    db.add(att)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="attachments", entity_id=str(att.id), after_data={"file": safe_name})
    db.commit()
    return {"id": att.id, "file_name": att.file_name}
