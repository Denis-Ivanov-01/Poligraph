from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.responses import RedirectResponse

from app.database import get_db
from app.dependencies import current_internal_user, root_admin_required
from app.models.political_party import PoliticalParty
from app.models.politician import Politician
from app.models.statement import Statement
from app.routers.internal.utils import render
from app.security import validate_csrf
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/internal/statements", tags=["internal-statements"])


def statements_query():
    return (
        select(Statement)
        .where(Statement.is_deleted.is_(False))
        .options(selectinload(Statement.politician), selectinload(Statement.party_at_statement_time))
        .order_by(Statement.created_at.desc())
    )


def statement_form_options(db: Session) -> dict:
    return {
        "politicians": db.scalars(select(Politician).where(Politician.is_deleted.is_(False)).order_by(Politician.full_name)).all(),
        "parties": db.scalars(select(PoliticalParty).where(PoliticalParty.is_deleted.is_(False)).order_by(PoliticalParty.full_name)).all(),
    }


@router.get("")
def statements(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    return render(request, "internal/statements.html", {"user": user, "statements": db.scalars(statements_query()).all()})


@router.get("/new")
def new_statement(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    context = {
        "user": user,
        "statement": None,
        "form_title": "New statement - step 1 of 3: draft details",
        "form_note": "This is the initial draft step. The statement is not published from here.",
        "form_action": "/internal/statements",
        "submit_label": "Next",
    }
    context.update(statement_form_options(db))
    return render(request, "internal/statement_form.html", context)


@router.post("")
def create_statement(
    request: Request,
    title: str = Form(""),
    source_type: str = Form(...),
    source_url: str = Form(""),
    original_text: str = Form(...),
    statement_date: str = Form(""),
    politician_id: str = Form(...),
    party_at_statement_time_id: str = Form(""),
    internal_notes: str = Form(""),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    statement = Statement(
        title=title.strip() or None,
        source_type=source_type,
        source_url=source_url or None,
        original_text=original_text,
        statement_date=date.fromisoformat(statement_date) if statement_date else None,
        politician_id=politician_id,
        party_at_statement_time_id=party_at_statement_time_id or None,
        internal_notes=internal_notes or None,
    )
    db.add(statement)
    db.commit()
    write_audit_log(db, request, user, "create_statement", "statement", str(statement.id), {"title": title.strip() or None})
    return RedirectResponse(f"/internal/statements/{statement.id}/prompt", status_code=303)


@router.get("/{statement_id}/edit")
def edit_statement_form(
    statement_id: UUID,
    request: Request,
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    statement = db.scalar(statements_query().where(Statement.id == statement_id))
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    context = {
        "user": user,
        "statement": statement,
        "form_title": "Edit statement",
        "form_note": "Update the draft or published statement fields.",
        "form_action": f"/internal/statements/{statement_id}/edit",
        "submit_label": "Save changes",
    }
    context.update(statement_form_options(db))
    return render(request, "internal/statement_form.html", context)


@router.post("/{statement_id}/edit")
def update_statement(
    statement_id: UUID,
    request: Request,
    title: str = Form(""),
    source_type: str = Form(...),
    source_url: str = Form(""),
    original_text: str = Form(...),
    statement_date: str = Form(""),
    politician_id: str = Form(...),
    party_at_statement_time_id: str = Form(""),
    internal_notes: str = Form(""),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    statement = db.scalar(statements_query().where(Statement.id == statement_id))
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    statement.title = title.strip() or None
    statement.source_type = source_type
    statement.source_url = source_url or None
    statement.original_text = original_text
    statement.statement_date = date.fromisoformat(statement_date) if statement_date else None
    statement.politician_id = politician_id
    statement.party_at_statement_time_id = party_at_statement_time_id or None
    statement.internal_notes = internal_notes or None
    db.commit()
    write_audit_log(db, request, user, "update_statement", "statement", str(statement.id), {"title": statement.title})
    return RedirectResponse("/internal/statements", status_code=303)


@router.post("/{statement_id}/delete")
def delete_statement(
    statement_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(root_admin_required),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    statement = db.get(Statement, statement_id)
    if statement:
        statement.is_deleted = True
        db.commit()
        write_audit_log(db, request, user, "delete_statement", "statement", str(statement.id), {"title": statement.title})
    return RedirectResponse("/internal/statements", status_code=303)


@router.get("/{statement_id}/preview")
def preview(statement_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    statement = db.scalar(statements_query().where(Statement.id == statement_id))
    return render(request, "internal/statement_preview.html", {"user": user, "statement": statement})
