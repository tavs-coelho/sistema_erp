from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import settings
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Attachment, AuditLog, Department, FiscalYear, RoleEnum, User
from ..schemas import DepartmentCreate, DepartmentOut, UserCreate, UserOut
from ..security import hash_password

router = APIRouter(prefix="/core", tags=["core"])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.read_only))):
    return db.query(User).order_by(User.id).all()


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin))):
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


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Department).order_by(Department.name).all()


@router.post("/departments", response_model=DepartmentOut)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin))):
    dep = Department(name=payload.name)
    db.add(dep)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="departments", entity_id=str(dep.id), after_data={"name": dep.name})
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
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.read_only)),
):
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
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
    path = upload_dir / file.filename
    path.write_bytes(file.file.read())
    att = Attachment(entity_type=entity_type, entity_id=entity_id, file_name=file.filename, path=str(path))
    db.add(att)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="attachments", entity_id=str(att.id), after_data={"file": file.filename})
    db.commit()
    return {"id": att.id, "file_name": att.file_name}
