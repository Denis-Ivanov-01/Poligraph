from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
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


def party_options(db: Session):
    return db.scalars(select(PoliticalParty).where(PoliticalParty.is_deleted.is_(False)).order_by(PoliticalParty.full_name)).all()


def politician_query():
    return select(Politician).where(Politician.is_deleted.is_(False)).options(selectinload(Politician.memberships)).order_by(Politician.full_name)


def current_membership(politician: Politician) -> PartyMembership | None:
    memberships = [membership for membership in politician.memberships if membership.end_date is None]
    memberships.sort(key=lambda item: item.start_date or date.min, reverse=True)
    return memberships[0] if memberships else None


def set_current_party(db: Session, politician: Politician, party_id: str) -> None:
    current = current_membership(politician)
    if current and str(current.party_id) == party_id:
        return

    today = date.today()
    for membership in politician.memberships:
        if membership.end_date is None:
            membership.end_date = today

    if party_id:
        db.add(PartyMembership(politician_id=politician.id, party_id=party_id, start_date=today))


@router.get("")
def politicians(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Politician).where(Politician.is_deleted.is_(False)).order_by(Politician.full_name)).all()
    return render(request, "internal/politicians.html", {"user": user, "politicians": items})


@router.get("/new")
def new_politician(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    return render(
        request,
        "internal/politician_form.html",
        {
            "user": user,
            "politician": None,
            "parties": party_options(db),
            "current_party_id": "",
            "form_title": "New politician",
            "form_action": "/internal/politicians",
            "submit_label": "Create politician",
        },
    )


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
    set_current_party(db, politician, party_id)
    db.commit()
    write_audit_log(db, request, user, "create_politician", "politician", str(politician.id), {"slug": slug})
    return RedirectResponse("/internal/politicians", status_code=303)


@router.get("/{politician_id}/edit")
def edit_politician_form(
    politician_id: UUID,
    request: Request,
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    politician = db.scalar(politician_query().where(Politician.id == politician_id))
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    membership = current_membership(politician)
    return render(
        request,
        "internal/politician_form.html",
        {
            "user": user,
            "politician": politician,
            "parties": party_options(db),
            "current_party_id": str(membership.party_id) if membership else "",
            "form_title": "Edit politician",
            "form_action": f"/internal/politicians/{politician.id}/edit",
            "submit_label": "Save changes",
        },
    )


@router.post("/{politician_id}/edit")
def update_politician(
    politician_id: UUID,
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
    politician = db.scalar(politician_query().where(Politician.id == politician_id))
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    politician.slug = slug
    politician.full_name = full_name
    politician.biography = biography or None
    politician.image_url = image_url or None
    set_current_party(db, politician, party_id)
    db.commit()
    write_audit_log(db, request, user, "update_politician", "politician", str(politician.id), {"slug": slug})
    return RedirectResponse("/internal/politicians", status_code=303)
