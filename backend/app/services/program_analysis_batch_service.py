import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_analysis import AiRun
from app.models.commitment import Commitment
from app.models.program import ProgramSection
from app.services.commitment_analysis_methodology import COMMITMENT_ANALYSIS_METHODOLOGY_VERSION, DEFAULT_BATCH_TRANCHE_SIZE
from app.services.program_ai_workflow_service import (
    COMMITMENT_STATUS_TASK,
    PROGRAM_AI_PROMPT_VERSION,
    PROGRAM_AI_SCHEMA_VERSION,
    SECTION_BATCH_STATUS_TASK,
    TARGET_SECTION_REF,
    batch_commitment_ref_map,
    build_commitment_status_prompt,
    build_section_batch_status_prompt,
    section_scope_commitments,
)


FAILED_ITEM_STATUSES = {"parse_failed", "import_failed", "no_import"}
COMPLETE_ITEM_STATUSES = {"imported"}


def _item_recommends_review(item: AiRun) -> bool:
    telemetry = item.telemetry or {}
    return bool(telemetry.get("human_review_recommended") or telemetry.get("review_reason_codes"))


def _user_id(user: dict | None):
    moderator = user.get("moderator") if user else None
    return moderator.id if moderator else None


def _fingerprint(snapshot: dict[str, Any], refs: dict[str, Any]) -> str:
    value = json.dumps({"input_snapshot": snapshot, "local_ref_map": refs}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sorted_scope(section: ProgramSection, recursive: bool) -> list[Commitment]:
    if recursive:
        return section_scope_commitments(section)
    return sorted(section.commitments, key=lambda item: (item.display_order, item.created_at or datetime.min.replace(tzinfo=timezone.utc)))


def create_section_analysis_batch(
    db: Session,
    section: ProgramSection,
    user: dict | None = None,
    *,
    recursive: bool = True,
    analysis_date: date | None = None,
    tranche_size: int = DEFAULT_BATCH_TRANCHE_SIZE,
) -> AiRun:
    commitments = _sorted_scope(section, recursive)
    if not commitments:
        raise ValueError("The selected section has no commitments in scope.")

    analysis_day = analysis_date or date.today()
    effective_tranche_size = max(1, tranche_size)
    local_ref_map = batch_commitment_ref_map(section, recursive=recursive)
    first_tranche_refs = [f"COM{index}" for index in range(1, min(len(commitments), effective_tranche_size) + 1)]
    snapshot = {
        "scope": "recursive" if recursive else "direct",
        "analysis_date": analysis_day.isoformat(),
        "target_ref": TARGET_SECTION_REF,
        "expected_commitment_refs": [f"COM{index}" for index in range(1, len(commitments) + 1)],
        "tranche_size": effective_tranche_size,
        "current_tranche_refs": first_tranche_refs,
        "completed_commitment_refs": [],
    }
    parent = AiRun(
        target_type="program_section",
        target_id=section.id,
        task_type=SECTION_BATCH_STATUS_TASK,
        execution_mode="manual_external_item_batch",
        status="in_progress",
        prompt_version=PROGRAM_AI_PROMPT_VERSION,
        schema_version=PROGRAM_AI_SCHEMA_VERSION,
        methodology_version=COMMITMENT_ANALYSIS_METHODOLOGY_VERSION,
        prompt_text=build_section_batch_status_prompt(section, recursive=recursive, commitment_refs=first_tranche_refs),
        input_snapshot=snapshot,
        local_ref_map=local_ref_map,
        input_fingerprint=_fingerprint(snapshot, local_ref_map),
        analysis_date=analysis_day,
        expected_item_count=len(commitments),
        completed_item_count=0,
        failed_item_count=0,
        human_review_item_count=0,
        retry_count=0,
        telemetry={"scope": snapshot["scope"], "calls_per_commitment": {}},
        structural_review_status="not_reviewed",
        factual_review_status="not_reviewed",
        created_by_user_id=_user_id(user),
    )
    db.add(parent)
    db.flush()

    for position, commitment in enumerate(commitments, start=1):
        commitment_ref = f"COM{position}"
        child_refs = {commitment_ref: local_ref_map[commitment_ref]}
        child_snapshot = {
            "analysis_date": analysis_day.isoformat(),
            "target_ref": commitment_ref,
            "batch_item_ref": commitment_ref,
            "batch_position": position,
            "batch_size": len(commitments),
        }
        child = AiRun(
            target_type="commitment",
            target_id=commitment.id,
            task_type=COMMITMENT_STATUS_TASK,
            execution_mode="manual_external_batch_item",
            status="prompt_generated",
            model_name=None,
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            methodology_version=COMMITMENT_ANALYSIS_METHODOLOGY_VERSION,
            prompt_text=build_commitment_status_prompt(
                commitment,
                commitment_ref=commitment_ref,
                analysis_date=analysis_day,
                batch_context=f"Commitment {position} of {len(commitments)}. Apply full standalone-quality research; do not use conclusions from other items.",
            ),
            input_snapshot=child_snapshot,
            local_ref_map=child_refs,
            input_fingerprint=_fingerprint(child_snapshot, child_refs),
            analysis_date=analysis_day,
            parent_ai_run_id=parent.id,
            batch_item_ref=commitment_ref,
            batch_position=position,
            retry_count=0,
            validation_errors=[],
            telemetry={},
            structural_review_status="not_reviewed",
            factual_review_status="not_reviewed",
            created_by_user_id=_user_id(user),
        )
        db.add(child)
    db.flush()
    refresh_batch_progress(db, parent)
    return parent


def get_section_analysis_batch(db: Session, batch_id: UUID, section_id: UUID | None = None, *, lock: bool = False) -> AiRun:
    query = select(AiRun).where(
        AiRun.id == batch_id,
        AiRun.task_type == SECTION_BATCH_STATUS_TASK,
        AiRun.parent_ai_run_id.is_(None),
    )
    if section_id:
        query = query.where(AiRun.target_type == "program_section", AiRun.target_id == section_id)
    if lock:
        query = query.with_for_update()
    batch = db.scalar(query)
    if not batch:
        raise ValueError("Section analysis batch not found.")
    return batch


def section_analysis_batch_items(db: Session, batch_id: UUID, *, lock: bool = False) -> list[AiRun]:
    query = select(AiRun).where(AiRun.parent_ai_run_id == batch_id).order_by(AiRun.batch_position)
    if lock:
        query = query.with_for_update()
    return list(db.scalars(query))


def next_batch_tranche_items(items: list[AiRun], *, tranche_size: int = DEFAULT_BATCH_TRANCHE_SIZE) -> list[AiRun]:
    size = max(1, tranche_size)
    pending = [item for item in items if item.status not in COMPLETE_ITEM_STATUSES]
    return pending[:size]


def batch_tranche_refs(items: list[AiRun], *, tranche_size: int = DEFAULT_BATCH_TRANCHE_SIZE) -> list[str]:
    return [item.batch_item_ref for item in next_batch_tranche_items(items, tranche_size=tranche_size) if item.batch_item_ref]


def get_section_analysis_batch_item(
    db: Session,
    batch: AiRun,
    *,
    item_id: UUID | None = None,
    item_ref: str | None = None,
    lock: bool = False,
) -> AiRun:
    query = select(AiRun).where(AiRun.parent_ai_run_id == batch.id)
    if item_id:
        query = query.where(AiRun.id == item_id)
    elif item_ref:
        query = query.where(AiRun.batch_item_ref == item_ref)
    else:
        raise ValueError("A batch item id or ref is required.")
    if lock:
        query = query.with_for_update()
    item = db.scalar(query)
    if not item:
        raise ValueError("Section analysis batch item not found.")
    return item


def record_batch_item_failure(item: AiRun, error: str) -> None:
    errors = list(item.validation_errors or [])
    errors.append({"at": datetime.now(timezone.utc).isoformat(), "message": error})
    item.validation_errors = errors
    item.retry_count = (item.retry_count or 0) + 1


def apply_invocation_telemetry(
    item: AiRun,
    *,
    model_name: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    tool_call_count: int | None = None,
) -> None:
    if model_name:
        item.model_name = model_name.strip()
    if input_tokens is not None:
        item.input_tokens = max(input_tokens, 0)
    if output_tokens is not None:
        item.output_tokens = max(output_tokens, 0)
    if tool_call_count is not None:
        item.tool_call_count = max(tool_call_count, 0)


def refresh_batch_progress(db: Session, batch: AiRun) -> dict[str, Any]:
    items = section_analysis_batch_items(db, batch.id)
    completed = [item for item in items if item.status in COMPLETE_ITEM_STATUSES]
    failed = [item for item in items if item.status in FAILED_ITEM_STATUSES]
    escalated = [item for item in completed if _item_recommends_review(item)]
    confidence_distribution = Counter(
        (item.telemetry or {}).get("confidence") for item in completed if (item.telemetry or {}).get("confidence")
    )
    source_urls = []
    source_count = 0
    for item in completed:
        source_count += int((item.telemetry or {}).get("sources_collected") or 0)
        for source in (item.parsed_json or {}).get("sources", []):
            if isinstance(source, dict) and source.get("url"):
                source_urls.append(source["url"].strip().lower().rstrip("/"))

    batch.expected_item_count = len(items)
    batch.completed_item_count = len(completed)
    batch.failed_item_count = len(failed)
    batch.human_review_item_count = len(escalated)
    batch.retry_count = sum(item.retry_count or 0 for item in items)
    if items and len(completed) == len(items):
        batch.status = "completed"
    elif failed:
        batch.status = "needs_attention"
    else:
        batch.status = "in_progress"
    batch.telemetry = {
        **(batch.telemetry or {}),
        "calls_per_commitment": {item.batch_item_ref: 1 + (item.retry_count or 0) for item in items},
        "tool_calls": sum(item.tool_call_count or 0 for item in items),
        "input_tokens": sum(item.input_tokens or 0 for item in items),
        "output_tokens": sum(item.output_tokens or 0 for item in items),
        "retry_count": batch.retry_count,
        "validation_failures": sum(len(item.validation_errors or []) for item in items),
        "escalated_commitment_refs": [item.batch_item_ref for item in escalated],
        "sources_collected": source_count,
        "unique_source_urls": len(set(source_urls)),
        "evidence_reuse_count": max(len(source_urls) - len(set(source_urls)), 0),
        "confidence_distribution": dict(confidence_distribution),
        "previous_status_disagreement_count": sum(
            1 for item in completed if (item.telemetry or {}).get("previous_status_disagreement")
        ),
    }
    return batch_progress_payload(batch, items)


def batch_progress_payload(batch: AiRun, items: list[AiRun]) -> dict[str, Any]:
    return {
        "batch_id": str(batch.id),
        "section_id": str(batch.target_id),
        "status": batch.status,
        "analysis_date": batch.analysis_date.isoformat() if batch.analysis_date else None,
        "execution_mode": batch.execution_mode,
        "model_name": batch.model_name,
        "prompt_version": batch.prompt_version,
        "schema_version": batch.schema_version,
        "methodology_version": batch.methodology_version,
        "input_tokens": batch.input_tokens,
        "output_tokens": batch.output_tokens,
        "tool_call_count": batch.tool_call_count,
        "expected_item_count": batch.expected_item_count,
        "completed_item_count": batch.completed_item_count,
        "failed_item_count": batch.failed_item_count,
        "pending_item_count": max(batch.expected_item_count - batch.completed_item_count - batch.failed_item_count, 0),
        "human_review_item_count": batch.human_review_item_count,
        "retry_count": batch.retry_count,
        "summary_ready": batch.status == "completed",
        "telemetry": batch.telemetry or {},
        "items": [
            {
                "ai_run_id": str(item.id),
                "commitment_id": str(item.target_id),
                "commitment_ref": item.batch_item_ref,
                "position": item.batch_position,
                "status": item.status,
                "retry_count": item.retry_count or 0,
                "validation_errors": item.validation_errors or [],
                "human_review_recommended": _item_recommends_review(item),
                "model_name": item.model_name,
                "input_tokens": item.input_tokens,
                "output_tokens": item.output_tokens,
                "tool_call_count": item.tool_call_count,
            }
            for item in items
        ],
    }
