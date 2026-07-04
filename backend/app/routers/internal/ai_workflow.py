from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.responses import RedirectResponse

from app.database import get_db
from app.dependencies import current_internal_user
from app.models.ai_analysis import AiAnalysis
from app.models.statement import Statement
from app.routers.internal.utils import render
from app.security import validate_csrf
from app.services.ai_json_validation_service import validate_ai_json
from app.services.ai_prompt_service import build_statement_prompt
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/internal/statements", tags=["internal-ai-workflow"])


def calculated_overall_score(scores) -> int:
    return int(
        round(
            (
                scores.factual_accuracy
                + scores.logical_consistency
                + scores.communicational_integrity
                + scores.principle_consistency
            )
            / 4
        )
    )


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
    prompt = build_statement_prompt(statement, previous_statements_for_prompt(db, statement))
    return render(request, "internal/prompt.html", {"user": user, "statement": statement, "prompt": prompt})


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
    write_audit_log(db, request, user, "generate_ai_prompt", "statement", str(statement.id))
    return RedirectResponse(f"/internal/statements/{statement.id}/prompt", status_code=303)


@router.get("/{statement_id}/ai-json")
def ai_json_form(statement_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    statement = get_statement(db, statement_id)
    return render(request, "internal/ai_json.html", {"user": user, "statement": statement})


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
    analysis = statement.ai_analysis or AiAnalysis(statement_id=statement.id)
    analysis.model_name = data.model_name
    analysis.prompt_version = data.prompt_version
    analysis.schema_version = data.schema_version
    analysis.analysis_date = datetime.now(timezone.utc)
    analysis.factual_accuracy_score = data.scores.factual_accuracy
    analysis.logical_consistency_score = data.scores.logical_consistency
    analysis.communicational_integrity_score = data.scores.communicational_integrity
    analysis.principle_consistency_score = data.scores.principle_consistency
    analysis.overall_score = calculated_overall_score(data.scores)
    analysis.factual_accuracy_explanation = data.explanations.factual_accuracy
    analysis.logical_consistency_explanation = data.explanations.logical_consistency
    analysis.communicational_integrity_explanation = data.explanations.communicational_integrity
    analysis.principle_consistency_explanation = data.explanations.principle_consistency
    analysis.overall_explanation = "Calculated automatically as the average of factual accuracy, logical consistency, communicational integrity, and principle consistency."
    if data.ai_details:
        analysis.prompt_text = data.ai_details.prompt_text
        analysis.raw_ai_response = data.ai_details.raw_ai_response
    else:
        analysis.prompt_text = build_statement_prompt(statement, previous_statements_for_prompt(db, statement))
        analysis.raw_ai_response = raw_json
    analysis.source_urls = [item.model_dump() for item in data.source_urls]
    analysis.is_published = False
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
