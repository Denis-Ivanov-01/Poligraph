from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.ai_analysis import AiRun
from app.models.commitment import Commitment
from app.models.program import Program, ProgramSection
from app.services.commitment_analysis_methodology import DEFAULT_BATCH_TRANCHE_SIZE
from app.services.commitment_service import optional_text, unset_other_active_programs
from app.services.program_ai_workflow_service import (
    COMMITMENT_STATUS_TASK,
    PROGRAM_STRUCTURE_TASK,
    SECTION_REFINEMENT_TASK,
    ai_run_context,
    build_program_structure_prompt,
    build_commitment_status_prompt,
    build_section_refinement_prompt,
    create_or_update_ai_run,
    import_commitment_status,
    import_section_refinement,
    import_structure,
    latest_ai_run,
    mark_import_failed,
    mark_no_import,
    mark_parse_failed,
    mark_parse_success,
    parse_json,
    program_structure_prompt_validation_error,
    source_retrieval_failed,
)
from app.services.program_analysis_batch_service import (
    apply_invocation_telemetry,
    batch_progress_payload,
    create_section_analysis_batch,
    get_section_analysis_batch,
    get_section_analysis_batch_item,
    record_batch_item_failure,
    refresh_batch_progress,
    section_analysis_batch_items,
)
from app.services.revision_service import create_entity_revision


STRUCTURAL_REVIEW_STATUSES = {"passed", "failed", "needs_fix"}


def ai_run_metadata(ai_run: AiRun) -> dict[str, Any]:
    return {
        "id": str(ai_run.id),
        "status": ai_run.status,
        "target_type": ai_run.target_type,
        "target_id": str(ai_run.target_id) if ai_run.target_id else None,
        "task_type": ai_run.task_type,
        "execution_mode": ai_run.execution_mode,
        "model_name": ai_run.model_name,
        "prompt_version": ai_run.prompt_version,
        "schema_version": ai_run.schema_version,
        "methodology_version": ai_run.methodology_version,
        "analysis_date": ai_run.analysis_date.isoformat() if ai_run.analysis_date else None,
        "input_tokens": ai_run.input_tokens,
        "output_tokens": ai_run.output_tokens,
        "tool_call_count": ai_run.tool_call_count,
    }


class ProgramWorkflowError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class PromptResult:
    program: Program
    ai_run: AiRun
    prompt: str
    target_type: str
    target_id: UUID
    task_type: str
    section: ProgramSection | None = None

    def to_dict(self, *, include_prompt: bool = True) -> dict[str, Any]:
        payload = {
            "ok": True,
            "program_id": str(self.program.id),
            "program_title": self.program.title,
            "target_type": self.target_type,
            "target_id": str(self.target_id),
            "task_type": self.task_type,
            "ai_run_id": str(self.ai_run.id),
            "ai_run_status": self.ai_run.status,
            "prompt_version": self.ai_run.prompt_version,
            "schema_version": self.ai_run.schema_version,
            "methodology_version": self.ai_run.methodology_version,
            "model_name": self.ai_run.model_name,
            "execution_mode": self.ai_run.execution_mode,
            "analysis_date": self.ai_run.analysis_date.isoformat() if self.ai_run.analysis_date else None,
            "ai_run": ai_run_metadata(self.ai_run),
        }
        if self.section:
            payload["section_id"] = str(self.section.id)
            payload["section_title"] = self.section.title
        if include_prompt:
            payload["prompt"] = self.prompt
        return payload


@dataclass
class JsonImportResult:
    ok: bool
    program: Program
    ai_run: AiRun
    raw_json: str
    imported_count: int = 0
    error: str | None = None
    error_kind: str | None = None
    status_code: int = 200
    data: dict[str, Any] | None = None
    section: ProgramSection | None = None
    commitment: Commitment | None = None
    batch_progress: dict[str, Any] | None = None

    def to_dict(self, *, include_response: bool = False) -> dict[str, Any]:
        payload = {
            "ok": self.ok,
            "program_id": str(self.program.id),
            "program_title": self.program.title,
            "ai_run_id": str(self.ai_run.id),
            "ai_run_status": self.ai_run.status,
            "model_name": self.ai_run.model_name,
            "prompt_version": self.ai_run.prompt_version,
            "schema_version": self.ai_run.schema_version,
            "methodology_version": self.ai_run.methodology_version,
            "execution_mode": self.ai_run.execution_mode,
            "analysis_date": self.ai_run.analysis_date.isoformat() if self.ai_run.analysis_date else None,
            "ai_run": ai_run_metadata(self.ai_run),
            "imported_count": self.imported_count,
            "status_code": self.status_code,
            "error": self.error,
            "error_kind": self.error_kind,
        }
        if self.section:
            payload["section_id"] = str(self.section.id)
            payload["section_title"] = self.section.title
        if self.commitment:
            payload["commitment_id"] = str(self.commitment.id)
            payload["commitment_title"] = self.commitment.title
        if self.batch_progress:
            payload["batch_progress"] = self.batch_progress
        if include_response:
            payload["raw_ai_response"] = self.raw_json
            payload["parsed_json"] = self.data
        return payload


@dataclass
class StructuralReviewResult:
    program: Program
    status: str
    note: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "program_id": str(self.program.id),
            "program_title": self.program.title,
            "structural_review_status": self.status,
            "structural_review_note": self.note,
        }


@dataclass
class PublishResult:
    program: Program
    commitment_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "program_id": str(self.program.id),
            "program_title": self.program.title,
            "is_published": self.program.is_published,
            "status": self.program.status,
            "published_at": self.program.published_at.isoformat() if self.program.published_at else None,
            "commitment_count": self.commitment_count,
        }


@dataclass
class BatchAnalysisResult:
    section: ProgramSection
    batch: AiRun
    items: list[AiRun]
    progress: dict[str, Any]

    def to_dict(self, *, include_prompts: bool = False) -> dict[str, Any]:
        payload = {
            "ok": True,
            "program_id": str(self.section.program_id),
            "program_title": self.section.program.title,
            "section_id": str(self.section.id),
            "section_title": self.section.title,
            "ai_run": ai_run_metadata(self.batch),
            **self.progress,
        }
        if include_prompts:
            prompts = {str(item.id): item.prompt_text for item in self.items}
            for item in payload["items"]:
                item["prompt"] = prompts[item["ai_run_id"]]
        return payload


def program_query():
    return (
        select(Program)
        .where(Program.is_deleted.is_(False))
        .options(selectinload(Program.related_party), selectinload(Program.sections))
    )


def get_program_for_workflow(db: Session, program_id: UUID) -> Program:
    program = db.scalar(program_query().where(Program.id == program_id))
    if not program:
        raise ProgramWorkflowError("Program not found", 404)
    return program


def get_section_for_workflow(db: Session, section_id: UUID) -> ProgramSection:
    section = db.get(ProgramSection, section_id)
    if not section or section.program.is_deleted:
        raise ProgramWorkflowError("Section not found", 404)
    return section


def get_commitment_for_workflow(db: Session, commitment_id: UUID) -> Commitment:
    commitment = db.get(Commitment, commitment_id)
    if not commitment or commitment.program.is_deleted:
        raise ProgramWorkflowError("Commitment not found", 404)
    return commitment


def get_ai_run_for_workflow(
    db: Session,
    ai_run_id: UUID | None,
    target_type: str,
    target_id: UUID,
    task_type: str,
) -> AiRun | None:
    if not ai_run_id:
        return latest_ai_run(db, target_type, target_id, task_type)
    ai_run = db.get(AiRun, ai_run_id)
    if not ai_run or ai_run.target_type != target_type or ai_run.target_id != target_id or ai_run.task_type != task_type:
        raise ProgramWorkflowError("AI run not found", 404)
    return ai_run


def ensure_ai_run_for_import(
    db: Session,
    ai_run_id: UUID | None,
    target_type: str,
    target_id: UUID,
    task_type: str,
    prompt_text: str,
    user: dict | None,
    run_context: dict | None = None,
) -> AiRun:
    if ai_run_id:
        ai_run = db.scalar(select(AiRun).where(AiRun.id == ai_run_id).with_for_update())
        if not ai_run or ai_run.target_type != target_type or ai_run.target_id != target_id or ai_run.task_type != task_type:
            raise ProgramWorkflowError("AI run not found", 404)
        return ai_run

    ai_run = get_ai_run_for_workflow(db, None, target_type, target_id, task_type)
    if ai_run:
        locked = db.scalar(select(AiRun).where(AiRun.id == ai_run.id).with_for_update())
        if locked:
            return locked

    ai_run = create_or_update_ai_run(db, target_type, target_id, task_type, prompt_text, user, **(run_context or {}))
    db.flush()
    db.commit()
    locked = db.scalar(select(AiRun).where(AiRun.id == ai_run.id).with_for_update())
    if not locked:
        raise ProgramWorkflowError("AI run could not be created", 500)
    return locked


def revise_program_structure(db: Session, program: Program, user: dict | None, note: str) -> None:
    db.flush()
    create_entity_revision(db, program, user, note)
    for section in db.scalars(select(ProgramSection).where(ProgramSection.program_id == program.id)):
        create_entity_revision(db, section, user, note)
    for commitment in db.scalars(select(Commitment).where(Commitment.program_id == program.id)):
        create_entity_revision(db, commitment, user, note)


def generate_program_structure_prompt(db: Session, program_id: UUID, user: dict | None = None) -> PromptResult:
    program = get_program_for_workflow(db, program_id)
    prompt_error = program_structure_prompt_validation_error(program)
    if prompt_error:
        raise ProgramWorkflowError(prompt_error, 400)
    prompt = build_program_structure_prompt(program)
    ai_run = create_or_update_ai_run(
        db,
        "program",
        program.id,
        PROGRAM_STRUCTURE_TASK,
        prompt,
        user,
        **ai_run_context(program, PROGRAM_STRUCTURE_TASK),
    )
    db.commit()
    return PromptResult(program, ai_run, prompt, "program", program.id, PROGRAM_STRUCTURE_TASK)


def generate_section_refinement_prompt(db: Session, section_id: UUID, user: dict | None = None) -> PromptResult:
    section = get_section_for_workflow(db, section_id)
    prompt = build_section_refinement_prompt(section)
    ai_run = create_or_update_ai_run(
        db,
        "program_section",
        section.id,
        SECTION_REFINEMENT_TASK,
        prompt,
        user,
        **ai_run_context(section, SECTION_REFINEMENT_TASK),
    )
    db.commit()
    return PromptResult(section.program, ai_run, prompt, "program_section", section.id, SECTION_REFINEMENT_TASK, section=section)


def generate_commitment_status_prompt(db: Session, commitment_id: UUID, user: dict | None = None) -> PromptResult:
    commitment = get_commitment_for_workflow(db, commitment_id)
    try:
        prompt = build_commitment_status_prompt(commitment)
    except ValueError as exc:
        raise ProgramWorkflowError(str(exc), 400) from exc
    ai_run = create_or_update_ai_run(
        db,
        "commitment",
        commitment.id,
        COMMITMENT_STATUS_TASK,
        prompt,
        user,
        **ai_run_context(commitment, COMMITMENT_STATUS_TASK),
    )
    db.commit()
    return PromptResult(commitment.program, ai_run, prompt, "commitment", commitment.id, COMMITMENT_STATUS_TASK)


def start_section_status_batch(
    db: Session,
    section_id: UUID,
    user: dict | None = None,
    *,
    recursive: bool = True,
    tranche_size: int = DEFAULT_BATCH_TRANCHE_SIZE,
) -> BatchAnalysisResult:
    section = get_section_for_workflow(db, section_id)
    try:
        batch = create_section_analysis_batch(db, section, user, recursive=recursive, tranche_size=tranche_size)
        progress = refresh_batch_progress(db, batch)
        db.commit()
    except (ValueError, SQLAlchemyError) as exc:
        db.rollback()
        message = str(exc) if isinstance(exc, ValueError) else "The section analysis batch could not be created."
        raise ProgramWorkflowError(message, 400) from exc
    items = section_analysis_batch_items(db, batch.id)
    return BatchAnalysisResult(section, batch, items, progress)


def load_section_status_batch(db: Session, section_id: UUID, batch_id: UUID) -> BatchAnalysisResult:
    section = get_section_for_workflow(db, section_id)
    try:
        batch = get_section_analysis_batch(db, batch_id, section.id)
        items = section_analysis_batch_items(db, batch.id)
        progress = batch_progress_payload(batch, items)
    except ValueError as exc:
        raise ProgramWorkflowError(str(exc), 404) from exc
    return BatchAnalysisResult(section, batch, items, progress)


def _store_ai_run_failure(
    db: Session,
    ai_run_id: UUID,
    raw_json: str,
    data: dict[str, Any] | None,
    error: str,
    user: dict | None,
) -> AiRun:
    db.rollback()
    ai_run = db.get(AiRun, ai_run_id)
    if not ai_run:
        raise ProgramWorkflowError("AI run was not available after import rollback", 500)
    if data is None:
        mark_parse_failed(ai_run, raw_json, error, user)
    else:
        mark_import_failed(ai_run, raw_json, data, error, user)
    db.commit()
    return ai_run


def import_program_structure_json(
    db: Session,
    program_id: UUID,
    raw_json: str,
    ai_run_id: UUID | None = None,
    user: dict | None = None,
) -> JsonImportResult:
    program = get_program_for_workflow(db, program_id)
    ai_run = ensure_ai_run_for_import(
        db,
        ai_run_id,
        "program",
        program.id,
        PROGRAM_STRUCTURE_TASK,
        build_program_structure_prompt(program),
        user,
        ai_run_context(program, PROGRAM_STRUCTURE_TASK),
    )
    if ai_run.status in {"imported", "no_import"}:
        return JsonImportResult(
            False,
            program,
            ai_run,
            raw_json,
            error="This AI run already has an import outcome. Generate a new prompt before importing again.",
            error_kind="already_imported",
            status_code=409,
        )

    data = None
    try:
        data = parse_json(raw_json)
        imported_count = import_structure(db, program, data, ai_run)
        if source_retrieval_failed(data):
            error = "Source retrieval failed. No sections or commitments were imported."
            mark_no_import(ai_run, raw_json, data, error, user)
            create_entity_revision(db, program, user, "program_source_not_found")
            db.commit()
            return JsonImportResult(
                False,
                program,
                ai_run,
                raw_json,
                error=error,
                error_kind="source_retrieval_failed",
                status_code=400,
                data=data,
            )
        mark_parse_success(ai_run, raw_json, data, user)
        revise_program_structure(db, program, user, "program_structure_imported")
        db.commit()
        return JsonImportResult(True, program, ai_run, raw_json, imported_count=imported_count, data=data)
    except ValueError as exc:
        error = str(exc)
        ai_run = _store_ai_run_failure(db, ai_run.id, raw_json, data, error, user)
        return JsonImportResult(False, program, ai_run, raw_json, error=error, error_kind="parse_failed", status_code=400, data=data)
    except SQLAlchemyError:
        error = (
            "The AI response was valid JSON, but it could not be saved to the database. "
            "Please check the response for duplicate or incomplete items and try again."
        )
        ai_run = _store_ai_run_failure(db, ai_run.id, raw_json, data, error, user)
        return JsonImportResult(False, program, ai_run, raw_json, error=error, error_kind="import_failed", status_code=400, data=data)


def import_section_refinement_json(
    db: Session,
    section_id: UUID,
    raw_json: str,
    ai_run_id: UUID | None = None,
    user: dict | None = None,
) -> JsonImportResult:
    section = get_section_for_workflow(db, section_id)
    ai_run = ensure_ai_run_for_import(
        db,
        ai_run_id,
        "program_section",
        section.id,
        SECTION_REFINEMENT_TASK,
        build_section_refinement_prompt(section),
        user,
        ai_run_context(section, SECTION_REFINEMENT_TASK),
    )
    if ai_run.status == "imported":
        return JsonImportResult(
            False,
            section.program,
            ai_run,
            raw_json,
            error="This AI run has already been imported. Generate a new prompt before importing again.",
            error_kind="already_imported",
            status_code=409,
            section=section,
        )

    data = None
    try:
        data = parse_json(raw_json)
        imported_count = import_section_refinement(db, section, data, ai_run)
        mark_parse_success(ai_run, raw_json, data, user)
        revise_program_structure(db, section.program, user, "section_refinement_imported")
        db.commit()
        return JsonImportResult(True, section.program, ai_run, raw_json, imported_count=imported_count, data=data, section=section)
    except (ValueError, SQLAlchemyError) as exc:
        error = str(exc) if isinstance(exc, ValueError) else "The validated refinement could not be saved. Check for duplicate or stale items and try again."
        ai_run = _store_ai_run_failure(db, ai_run.id, raw_json, data, error, user)
        return JsonImportResult(False, section.program, ai_run, raw_json, error=error, error_kind="import_failed", status_code=400, data=data, section=section)


def import_commitment_status_json(
    db: Session,
    commitment_id: UUID,
    raw_json: str,
    ai_run_id: UUID | None = None,
    user: dict | None = None,
    *,
    model_name: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    tool_call_count: int | None = None,
) -> JsonImportResult:
    commitment = get_commitment_for_workflow(db, commitment_id)
    ai_run = ensure_ai_run_for_import(
        db,
        ai_run_id,
        "commitment",
        commitment.id,
        COMMITMENT_STATUS_TASK,
        build_commitment_status_prompt(commitment),
        user,
        ai_run_context(commitment, COMMITMENT_STATUS_TASK),
    )
    if ai_run.status == "imported":
        return JsonImportResult(
            False,
            commitment.program,
            ai_run,
            raw_json,
            error="This AI run has already been imported. Generate a new prompt before importing again.",
            error_kind="already_imported",
            status_code=409,
            commitment=commitment,
        )

    data = None
    try:
        data = parse_json(raw_json)
        apply_invocation_telemetry(
            ai_run,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_call_count=tool_call_count,
        )
        import_commitment_status(db, commitment, data, ai_run, user)
        mark_parse_success(ai_run, raw_json, data, user)
        create_entity_revision(db, commitment, user, "commitment_status_imported")
        db.commit()
        return JsonImportResult(True, commitment.program, ai_run, raw_json, imported_count=1, data=data, commitment=commitment)
    except (ValueError, SQLAlchemyError) as exc:
        error = str(exc) if isinstance(exc, ValueError) else "The validated commitment analysis could not be saved."
        ai_run = _store_ai_run_failure(db, ai_run.id, raw_json, data, error, user)
        apply_invocation_telemetry(
            ai_run,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_call_count=tool_call_count,
        )
        db.commit()
        commitment = get_commitment_for_workflow(db, commitment_id)
        return JsonImportResult(
            False,
            commitment.program,
            ai_run,
            raw_json,
            error=error,
            error_kind="parse_failed" if data is None else "validation_failed",
            status_code=400,
            data=data,
            commitment=commitment,
        )


def import_section_status_batch_item_json(
    db: Session,
    section_id: UUID,
    batch_id: UUID,
    raw_json: str,
    *,
    item_id: UUID | None = None,
    item_ref: str | None = None,
    user: dict | None = None,
    model_name: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    tool_call_count: int | None = None,
) -> JsonImportResult:
    section = get_section_for_workflow(db, section_id)
    try:
        batch = get_section_analysis_batch(db, batch_id, section.id, lock=True)
        item = get_section_analysis_batch_item(db, batch, item_id=item_id, item_ref=item_ref, lock=True)
    except ValueError as exc:
        raise ProgramWorkflowError(str(exc), 404) from exc
    commitment = get_commitment_for_workflow(db, item.target_id)
    if item.status == "imported":
        progress = batch_progress_payload(batch, section_analysis_batch_items(db, batch.id))
        return JsonImportResult(
            False,
            section.program,
            item,
            raw_json,
            error="This batch item has already been imported.",
            error_kind="already_imported",
            status_code=409,
            section=section,
            commitment=commitment,
            batch_progress=progress,
        )

    data = None
    try:
        data = parse_json(raw_json)
        apply_invocation_telemetry(
            item,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_call_count=tool_call_count,
        )
        import_commitment_status(db, commitment, data, item, user)
        mark_parse_success(item, raw_json, data, user)
        create_entity_revision(db, commitment, user, "section_batch_item_status_imported")
        progress = refresh_batch_progress(db, batch)
        db.commit()
        return JsonImportResult(
            True,
            section.program,
            item,
            raw_json,
            imported_count=1,
            data=data,
            section=section,
            commitment=commitment,
            batch_progress=progress,
        )
    except (ValueError, SQLAlchemyError) as exc:
        error = str(exc) if isinstance(exc, ValueError) else "The validated batch item could not be saved."
        db.rollback()
        batch = get_section_analysis_batch(db, batch_id, section.id, lock=True)
        item = get_section_analysis_batch_item(db, batch, item_id=item_id, item_ref=item_ref, lock=True)
        if data is None:
            mark_parse_failed(item, raw_json, error, user)
        else:
            mark_import_failed(item, raw_json, data, error, user)
        record_batch_item_failure(item, error)
        apply_invocation_telemetry(
            item,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_call_count=tool_call_count,
        )
        progress = refresh_batch_progress(db, batch)
        db.commit()
        section = get_section_for_workflow(db, section_id)
        commitment = get_commitment_for_workflow(db, item.target_id)
        return JsonImportResult(
            False,
            section.program,
            item,
            raw_json,
            error=error,
            error_kind="parse_failed" if data is None else "validation_failed",
            status_code=400,
            data=data,
            section=section,
            commitment=commitment,
            batch_progress=progress,
        )


def approve_program_structure(
    db: Session,
    program_id: UUID,
    status: str = "passed",
    note: str = "",
    user: dict | None = None,
) -> StructuralReviewResult:
    if status not in STRUCTURAL_REVIEW_STATUSES:
        raise ProgramWorkflowError("Invalid structural review status", 400)
    program = get_program_for_workflow(db, program_id)
    program.structural_review_status = status
    program.structural_review_note = optional_text(note)
    create_entity_revision(db, program, user, "program_structural_review")
    db.commit()
    return StructuralReviewResult(program, status, program.structural_review_note)


def publish_program(db: Session, program_id: UUID, user: dict | None = None) -> PublishResult:
    program = get_program_for_workflow(db, program_id)
    if program.structural_review_status != "passed":
        raise ProgramWorkflowError("The program must pass structural review before publication.", 409)
    if program.is_active_government_program:
        unset_other_active_programs(db, program)
    program.is_published = True
    program.status = "published"
    program.published_at = datetime.now(timezone.utc)
    commitments = db.scalars(select(Commitment).where(Commitment.program_id == program.id)).all()
    for commitment in commitments:
        commitment.is_published = True
    revise_program_structure(db, program, user, "program_published")
    db.commit()
    return PublishResult(program, len(commitments))


def list_program_sections(db: Session, program_id: UUID) -> list[ProgramSection]:
    program = get_program_for_workflow(db, program_id)
    return sorted(program.sections, key=lambda section: (section.display_order, section.title))
    import_commitment_status,
