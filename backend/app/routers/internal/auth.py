from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.config import get_settings
from app.database import get_db
from app.models.moderator import Moderator
from app.routers.internal.utils import render
from app.security import clear_session, set_session, validate_csrf, verify_password
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/internal", tags=["internal-auth"])


@router.get("/login")
def login_form(request: Request):
    return render(request, "internal/login.html")


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    settings = get_settings()
    response = RedirectResponse("/internal", status_code=303)
    if settings.root_admin_enabled and username == settings.root_admin_username and verify_password(password, settings.root_admin_password_hash):
        set_session(response, {"role": "root_admin", "username": username, "csrf_token": csrf_token})
        write_audit_log(db, request, {"role": "root_admin", "username": username, "moderator": None}, "login", "session")
        return response
    moderator = db.scalar(select(Moderator).where(Moderator.username == username, Moderator.is_active.is_(True)))
    if moderator and verify_password(password, moderator.password_hash):
        set_session(response, {"role": "moderator", "moderator_id": str(moderator.id), "csrf_token": csrf_token})
        write_audit_log(db, request, {"role": "moderator", "moderator": moderator}, "login", "session")
        return response
    return render(request, "internal/login.html", {"error": "Invalid username or password"}, status_code=400)


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    response = RedirectResponse("/internal/login", status_code=303)
    clear_session(response)
    return response
