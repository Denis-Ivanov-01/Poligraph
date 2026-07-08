from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.responses import RedirectResponse

from app.database import get_db
from app.dependencies import current_internal_user
from app.models.statement import Statement
from app.routers.internal.utils import render
from app.security import validate_csrf
from app.services.ai_json_validation_service import validate_ai_json
from app.services.ai_prompt_service import build_statement_prompt
from app.services.audit_service import write_audit_log
from app.services.statement_analysis_service import apply_statement_ai_analysis

router = APIRouter(prefix="/internal/statements", tags=["internal-ai-workflow"])


def get_statement(db: Session, statement_id: UUID) -> Statement:
    return db.scalar(
        select(Statement)
        .where(Statement.id == statement_id)
        .options(
            selectinload(Statement.ai_analysis),
            selectinload(Statement.politician),
            selectinload(Statement.party_at_statement_time),
        )
    )


def previous_statements_for_prompt(db: Session, statement: Statement) -> list[Statement]:
    if not statement.politician_id or not statement.statement_date:
        return []
    return list(
        db.scalars(
            select(Statement)
            .where(
                Statement.id != statement.id,
                Statement.politician_id == statement.politician_id,
                Statement.statement_date < statement.statement_date,
                Statement.is_deleted.is_(False),
            )
            .options(
                selectinload(Statement.ai_analysis),
                selectinload(Statement.politician),
                selectinload(Statement.party_at_statement_time),
            )
            .order_by(Statement.statement_date.desc(), Statement.created_at.desc())
        )
    )


@router.get("/{statement_id}/prompt")
def prompt_page(statement_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    statement = get_statement(db, statement_id)
    if not statement.generated_prompt_text:
        statement.generated_prompt_text = build_statement_prompt(statement, previous_statements_for_prompt(db, statement))
        db.commit()
    prompt = statement.generated_prompt_text
    return render(request, "internal/prompt.html", {"user": user, "statement": statement, "prompt": prompt})


@router.post("/{statement_id}/prompt")
def save_prompt(
    statement_id: UUID,
    request: Request,
    prompt_text: str = Form(...),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    statement = get_statement(db, statement_id)
    statement.generated_prompt_text = prompt_text
    if statement.ai_analysis:
        statement.ai_analysis.prompt_text = prompt_text
    db.commit()
    write_audit_log(db, request, user, "save_ai_prompt", "statement", str(statement.id))
    return RedirectResponse(f"/internal/statements/{statement.id}/ai-json", status_code=303)


@router.post("/{statement_id}/generate-prompt")
def generate_prompt(
    statement_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    statement = get_statement(db, statement_id)
    statement.generated_prompt_text = build_statement_prompt(statement, previous_statements_for_prompt(db, statement))
    if statement.ai_analysis:
        statement.ai_analysis.prompt_text = statement.generated_prompt_text
    db.commit()
    write_audit_log(db, request, user, "generate_ai_prompt", "statement", str(statement.id))
    return RedirectResponse(f"/internal/statements/{statement.id}/prompt", status_code=303)


@router.get("/{statement_id}/ai-json")
def ai_json_form(statement_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    statement = get_statement(db, statement_id)
    raw_json = statement.ai_analysis.raw_ai_response if statement.ai_analysis else ""
    return render(request, "internal/ai_json.html", {"user": user, "statement": statement, "raw_json": raw_json})


@router.post("/{statement_id}/ai-json")
def save_ai_json(
    statement_id: UUID,
    request: Request,
    raw_json: str = Form(...),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    statement = get_statement(db, statement_id)
    try:
        data = validate_ai_json(raw_json)
    except ValueError as exc:
        return render(request, "internal/ai_json.html", {"user": user, "statement": statement, "error": str(exc), "raw_json": raw_json}, status_code=400)
    prompt_text = statement.generated_prompt_text or build_statement_prompt(statement, previous_statements_for_prompt(db, statement))
    analysis = apply_statement_ai_analysis(statement, data, raw_json, prompt_text)
    db.add(analysis)
    db.commit()
    write_audit_log(db, request, user, "save_ai_json", "statement", str(statement.id), {"valid": True})
    return RedirectResponse(f"/internal/statements/{statement.id}/preview", status_code=303)


@router.post("/{statement_id}/publish")
def publish_statement(
    statement_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    statement = get_statement(db, statement_id)
    if not statement.ai_analysis:
        return render(request, "internal/statement_preview.html", {"user": user, "statement": statement, "error": "AI analysis is required before publishing"}, status_code=400)
    statement.status = "published"
    statement.published_at = datetime.now(timezone.utc)
    statement.ai_analysis.is_published = True
    db.commit()
    write_audit_log(db, request, user, "publish_statement", "statement", str(statement.id))
    return RedirectResponse("/internal/statements", status_code=303)
