from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Asset, AssetMovement, RoleEnum, User
from ..schemas import AssetCreate

router = APIRouter(prefix="/patrimony", tags=["patrimony"])


@router.get("/assets")
def list_assets(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Asset).order_by(Asset.id).all()


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
def transfer_asset(asset_id: int, to_department_id: int, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.patrimony))):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Bem não encontrado")
    movement = AssetMovement(asset_id=asset.id, from_department_id=asset.department_id, to_department_id=to_department_id, movement_type="transferencia")
    asset.department_id = to_department_id
    db.add(movement)
    write_audit(db, user_id=current.id, action="update", entity="assets", entity_id=str(asset.id), after_data={"department_id": to_department_id})
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
def assets_by_department(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    data = {}
    for asset in db.query(Asset).all():
        data.setdefault(asset.department_id, []).append(asset.tag)
    return data


@router.get("/movements")
def movement_history(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(AssetMovement).order_by(AssetMovement.moved_at.desc()).all()
