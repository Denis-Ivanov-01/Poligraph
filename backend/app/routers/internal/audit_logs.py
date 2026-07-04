from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_internal_user
from app.models.audit_log import AuditLog
from app.routers.internal.utils import render

router = APIRouter(prefix="/internal/audit-logs", tags=["internal-audit-logs"])


@router.get("")
def audit_logs(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    items = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all()
    return render(request, "internal/audit_logs.html", {"user": user, "logs": items})
