from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.database import get_db
from app.dependencies import current_internal_user
from app.models.political_party import PoliticalParty
from app.routers.internal.utils import render
from app.security import validate_csrf
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/internal/parties", tags=["internal-parties"])


@router.get("")
def parties(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    items = db.scalars(select(PoliticalParty).where(PoliticalParty.is_deleted.is_(False)).order_by(PoliticalParty.full_name)).all()
    return render(request, "internal/parties.html", {"user": user, "parties": items})


@router.get("/new")
def new_party(request: Request, user: dict = Depends(current_internal_user)):
    return render(request, "internal/party_form.html", {"user": user})


@router.post("")
def create_party(
    request: Request,
    slug: str = Form(...),
    full_name: str = Form(...),
    short_name: str = Form(...),
    description: str = Form(""),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    party = PoliticalParty(slug=slug, full_name=full_name, short_name=short_name, description=description or None)
    db.add(party)
    db.commit()
    write_audit_log(db, request, user, "create_party", "political_party", str(party.id), {"slug": slug})
    return RedirectResponse("/internal/parties", status_code=303)
