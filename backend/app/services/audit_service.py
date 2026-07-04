from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    request: Request,
    user: dict | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict | None = None,
) -> None:
    moderator = user.get("moderator") if user else None
    log = AuditLog(
        actor_type=user["role"] if user else "anonymous",
        actor_id=str(moderator.id) if moderator else user.get("username") if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=request.client.host if request.client else None,
    )
    db.add(log)
    db.commit()
