from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Asset, AssetMovement, RoleEnum, User
from ..schemas import AssetCreate, AssetTransferRequest

router = APIRouter(prefix="/patrimony", tags=["patrimony"])


@router.get("/assets")
def list_assets(
    search: str | None = None,
    department_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Asset)
    if search:
        q = q.filter(Asset.description.ilike(f"%{search}%"))
    if department_id:
        q = q.filter(Asset.department_id == department_id)
    total = q.count()
    items = q.order_by(Asset.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.post("/assets")
def create_asset(payload: AssetCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.patrimony))):
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="assets", entity_id=str(asset.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{asset_id}/transfer")
def transfer_asset(
    asset_id: int,
    payload: AssetTransferRequest,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.patrimony)),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Bem não encontrado")
    movement = AssetMovement(
        asset_id=asset.id,
        from_department_id=asset.department_id,
        to_department_id=payload.to_department_id,
        movement_type="transferencia",
    )
    asset.department_id = payload.to_department_id
    if payload.new_location:
        asset.location = payload.new_location
    if payload.new_responsible_employee_id:
        asset.responsible_employee_id = payload.new_responsible_employee_id
    db.add(movement)
    write_audit(
        db,
        user_id=current.id,
        action="update",
        entity="assets",
        entity_id=str(asset.id),
        after_data={
            "department_id": payload.to_department_id,
            "location": asset.location,
            "responsible_employee_id": asset.responsible_employee_id,
        },
    )
    db.commit()
    return {"message": "Transferido"}


@router.post("/assets/{asset_id}/write-off")
def write_off(asset_id: int, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.patrimony))):
    asset = db.get(Asset, asset_id)
    asset.status = "baixado"
    db.add(AssetMovement(asset_id=asset.id, from_department_id=asset.department_id, to_department_id=None, movement_type="baixa"))
    write_audit(db, user_id=current.id, action="update", entity="assets", entity_id=str(asset.id), after_data={"status": asset.status})
    db.commit()
    return {"message": "Bem baixado"}


@router.get("/inventory")
def inventory(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {"total": db.query(Asset).count(), "ativos": db.query(Asset).filter(Asset.status == "ativo").count()}


@router.get("/reports/by-department")
def assets_by_department(department_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    data = {}
    q = db.query(Asset)
    if department_id:
        q = q.filter(Asset.department_id == department_id)
    for asset in q.all():
        data.setdefault(asset.department_id, []).append(asset.tag)
    return data


@router.get("/movements")
def movement_history(
    asset_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(AssetMovement)
    if asset_id:
        q = q.filter(AssetMovement.asset_id == asset_id)
    total = q.count()
    items = q.order_by(AssetMovement.moved_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}
