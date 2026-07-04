from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.database import get_db
from app.dependencies import root_admin_required
from app.models.moderator import Moderator
from app.routers.internal.utils import render
from app.security import hash_password, validate_csrf
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/internal/moderators", tags=["internal-moderators"])


@router.get("")
def moderators(request: Request, user: dict = Depends(root_admin_required), db: Session = Depends(get_db)):
    items = db.scalars(select(Moderator).order_by(Moderator.username)).all()
    return render(request, "internal/moderators.html", {"user": user, "moderators": items})


@router.post("")
def create_moderator(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    user: dict = Depends(root_admin_required),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    moderator = Moderator(username=username, password_hash=hash_password(password))
    db.add(moderator)
    db.commit()
    write_audit_log(db, request, user, "create_moderator", "moderator", str(moderator.id), {"username": username})
    return RedirectResponse("/internal/moderators", status_code=303)


@router.post("/{moderator_id}/deactivate")
def deactivate_moderator(
    moderator_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(root_admin_required),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    moderator = db.get(Moderator, moderator_id)
    if moderator:
        moderator.is_active = False
        db.commit()
        write_audit_log(db, request, user, "deactivate_moderator", "moderator", str(moderator.id))
    return RedirectResponse("/internal/moderators", status_code=303)
