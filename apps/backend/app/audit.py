from sqlalchemy.orm import Session

from .models import AuditLog


def write_audit(db: Session, *, user_id: int | None, action: str, entity: str, entity_id: str, before_data=None, after_data=None):
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            before_data=before_data,
            after_data=after_data,
        )
    )
