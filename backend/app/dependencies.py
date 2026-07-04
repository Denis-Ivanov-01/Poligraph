from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.moderator import Moderator
from app.security import get_session


def current_internal_user(request: Request, db: Session = Depends(get_db)) -> dict:
    session = get_session(request)
    role = session.get("role")
    if role == "root_admin":
        return {"role": "root_admin", "username": session.get("username", "admin"), "moderator": None}
    if role == "moderator":
        moderator = db.get(Moderator, session.get("moderator_id"))
        if moderator and moderator.is_active:
            return {"role": "moderator", "username": moderator.username, "moderator": moderator}
    raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/internal/login"})


def root_admin_required(user: dict = Depends(current_internal_user)) -> dict:
    if user["role"] != "root_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Root Admin only")
    return user
