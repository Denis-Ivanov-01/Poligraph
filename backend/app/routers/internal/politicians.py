from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.responses import RedirectResponse

from app.database import get_db
from app.dependencies import current_internal_user
from app.models.party_membership import PartyMembership
from app.models.political_party import PoliticalParty
from app.models.politician import Politician
from app.routers.internal.utils import render
from app.security import validate_csrf
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/internal/politicians", tags=["internal-politicians"])


@router.get("")
def politicians(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Politician).where(Politician.is_deleted.is_(False)).order_by(Politician.full_name)).all()
    return render(request, "internal/politicians.html", {"user": user, "politicians": items})


@router.get("/new")
def new_politician(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    parties = db.scalars(select(PoliticalParty).where(PoliticalParty.is_deleted.is_(False)).order_by(PoliticalParty.full_name)).all()
    return render(request, "internal/politician_form.html", {"user": user, "parties": parties})


@router.post("")
def create_politician(
    request: Request,
    slug: str = Form(...),
    full_name: str = Form(...),
    biography: str = Form(""),
    image_url: str = Form(""),
    party_id: str = Form(""),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    politician = Politician(slug=slug, full_name=full_name, biography=biography or None, image_url=image_url or None)
    db.add(politician)
    db.flush()
    if party_id:
        db.add(PartyMembership(politician_id=politician.id, party_id=party_id, start_date=date.today()))
    db.commit()
    write_audit_log(db, request, user, "create_politician", "politician", str(politician.id), {"slug": slug})
    return RedirectResponse("/internal/politicians", status_code=303)
