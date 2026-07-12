from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.ai_analysis import AiRun, StatementAiAnalysis
from app.models.evidence import EvidenceItem
from app.models.statement import Statement
from app.models.statement_claim import StatementClaim, StatementClaimEvidenceLink
from app.schemas.ai_analysis import AiAnalysisInput


def calculated_overall_score(scores) -> int | None:
    values = [
        scores.factual_accuracy,
        scores.logical_consistency,
        scores.communicational_integrity,
        scores.principle_consistency,
    ]
    usable = [value for value in values if value is not None]
    return int(round(sum(usable) / len(usable))) if usable else None


def _user_id(user: dict | None) -> UUID | None:
    moderator = user.get("moderator") if user else None
    return moderator.id if moderator else None


def _parse_date(value: str | None) -> date | None:
    if not value or value == "YYYY-MM-DD or null":
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def create_statement_ai_run(
    db: Session,
    statement: Statement,
    prompt_text: str,
    user: dict | None = None,
) -> AiRun:
    ai_run = AiRun(
        target_type="statement",
        target_id=statement.id,
        task_type="statement_analysis",
        execution_mode="manual_external",
        status="prompt_generated",
        prompt_version="mvp-3",
        schema_version="mvp-3",
        prompt_text=prompt_text,
        structural_review_status="not_reviewed",
        factual_review_status="not_reviewed",
        created_by_user_id=_user_id(user),
    )
    statement.status = "prompt_generated"
    db.add(ai_run)
    return ai_run


def latest_statement_ai_run(db: Session, statement: Statement) -> AiRun | None:
    return (
        db.query(AiRun)
        .filter(AiRun.target_type == "statement", AiRun.target_id == statement.id, AiRun.task_type == "statement_analysis")
        .order_by(AiRun.created_at.desc())
        .first()
    )


def latest_or_create_statement_ai_run(
    db: Session,
    statement: Statement,
    prompt_text: str,
    user: dict | None = None,
) -> AiRun:
    ai_run = latest_statement_ai_run(db, statement)
    if ai_run:
        ai_run.prompt_text = prompt_text
        ai_run.status = "prompt_generated" if ai_run.status in {"prompt_generated", "parse_failed"} else ai_run.status
        return ai_run
    return create_statement_ai_run(db, statement, prompt_text, user)


def apply_statement_ai_analysis(
    db: Session,
    statement: Statement,
    data: AiAnalysisInput,
    raw_json: str,
    prompt_text: str,
) -> StatementAiAnalysis:
    ai_run = latest_or_create_statement_ai_run(db, statement, prompt_text)
    ai_run.model_name = data.model_name
    ai_run.prompt_version = data.prompt_version
    ai_run.schema_version = data.schema_version
    ai_run.raw_ai_response = raw_json
    ai_run.parsed_json = data.model_dump()
    ai_run.parse_error = None
    ai_run.status = "parsed"
    ai_run.response_pasted_at = datetime.now(timezone.utc)
    ai_run.parsed_at = datetime.now(timezone.utc)

    if statement.ai_analysis:
        old_claim_ids = [
            item[0]
            for item in db.query(StatementClaim.id)
            .filter(StatementClaim.statement_ai_analysis_id == statement.ai_analysis.id)
            .all()
        ]
        if old_claim_ids:
            db.execute(delete(StatementClaimEvidenceLink).where(StatementClaimEvidenceLink.claim_id.in_(old_claim_ids)))
            db.execute(delete(StatementClaim).where(StatementClaim.id.in_(old_claim_ids)))
        analysis = statement.ai_analysis
        analysis.ai_run_id = ai_run.id
    else:
        analysis = StatementAiAnalysis(statement_id=statement.id, ai_run_id=ai_run.id)

    statement_analysis = data.statement_analysis
    explanations = data.explanations
    analysis.analysis_date = datetime.now(timezone.utc)
    analysis.factual_accuracy_applicability = statement_analysis.get("factual_accuracy_applicability", "applicable")
    analysis.factual_accuracy_score = data.scores.factual_accuracy
    analysis.logical_consistency_score = data.scores.logical_consistency
    analysis.communicational_integrity_score = data.scores.communicational_integrity
    analysis.principle_consistency_score = data.scores.principle_consistency
    analysis.factual_accuracy_explanation = explanations.factual_accuracy
    analysis.logical_consistency_explanation = explanations.logical_consistency
    analysis.communicational_integrity_explanation = explanations.communicational_integrity
    analysis.principle_consistency_explanation = explanations.principle_consistency
    analysis.evidence_review_completeness = statement_analysis.get("evidence_review_completeness", "partial")
    analysis.human_review_recommended = bool(statement_analysis.get("human_review_recommended", False))
    analysis.human_review_reason = statement_analysis.get("human_review_reason")
    analysis.structural_review_status = "not_reviewed"
    analysis.factual_review_status = "not_reviewed"
    analysis.is_published = False
    statement.status = "parsed"
    db.add(analysis)
    db.flush()

    evidence_by_ref: dict[str, EvidenceItem] = {}
    for source in data.sources:
        evidence = EvidenceItem(
            title=source.get("title") or source.get("url") or "Untitled source",
            url=source.get("url") or "",
            source_type=source.get("source_type") or "other",
            publisher=source.get("publisher"),
            published_at=_parse_date(source.get("published_at")),
            quote_or_relevant_excerpt=source.get("quote_or_relevant_excerpt"),
            description=source.get("description"),
            reliability_level=source.get("reliability_level") or "medium",
            source_origin="ai_imported",
            structural_status="parsed",
            factual_review_status="not_reviewed",
            created_from_ai_run_id=ai_run.id,
        )
        db.add(evidence)
        db.flush()
        source_ref = source.get("source_ref")
        if source_ref:
            evidence_by_ref[source_ref] = evidence

    for index, claim_data in enumerate(data.claims, start=1):
        import_ref = claim_data.get("claim_ref")
        claim = StatementClaim(
            statement_id=statement.id,
            statement_ai_analysis_id=analysis.id,
            ai_run_id=ai_run.id,
            import_ref=import_ref,
            display_code=import_ref or f"C{index}",
            exact_quote=claim_data.get("exact_quote") or "",
            normalized_claim=claim_data.get("normalized_claim") or "",
            claim_type=claim_data.get("claim_type") or "mixed",
            checkability=claim_data.get("checkability") or "partially_checkable",
            materiality=claim_data.get("materiality") or "medium",
            materiality_reason=claim_data.get("materiality_reason"),
            ai_verification_status=claim_data.get("ai_verification_status") or "not_fact_checked",
            confidence_level=claim_data.get("confidence_level") or "medium",
            evidence_summary=claim_data.get("evidence_summary"),
            missing_or_uncertain_evidence=claim_data.get("missing_or_uncertain_evidence"),
            used_for_dimensions_json=claim_data.get("used_for_dimensions"),
            source_origin="ai_imported",
            structural_status="parsed",
            factual_review_status="not_reviewed",
            display_order=index,
        )
        db.add(claim)
        db.flush()
        for source_ref in claim_data.get("source_refs") or []:
            evidence = evidence_by_ref.get(source_ref)
            if not evidence:
                continue
            db.add(
                StatementClaimEvidenceLink(
                    claim_id=claim.id,
                    evidence_item_id=evidence.id,
                    relation_type="supports",
                    source_origin="ai_imported",
                    structural_status="parsed",
                    factual_review_status="not_reviewed",
                )
            )
    return analysis


def mark_ai_run_parse_failed(ai_run: AiRun, raw_json: str, parse_error: str) -> None:
    ai_run.raw_ai_response = raw_json
    ai_run.parse_error = parse_error
    ai_run.status = "parse_failed"
    ai_run.response_pasted_at = datetime.now(timezone.utc)
