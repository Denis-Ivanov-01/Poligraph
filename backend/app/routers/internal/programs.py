from uuid import UUID

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload
from starlette.responses import RedirectResponse

from app.database import get_db
from app.dependencies import current_internal_user, moderator_required, root_admin_required
from app.models.ai_analysis import AiRun
from app.models.commitment import Commitment, CommitmentEvidence, CommitmentStatusUpdate
from app.models.evidence import EvidenceItem
from app.models.media_asset import MediaAsset
from app.models.political_party import PoliticalParty
from app.models.program import Program, ProgramSection
from app.routers.internal.utils import render
from app.security import validate_csrf
from app.services.audit_service import write_audit_log
from app.services.commitment_service import (
    BASELINE_MODES,
    COMMITMENT_STATUSES,
    COMMITMENT_TYPES,
    CONFIDENCE_LEVELS,
    CONTRIBUTION_LEVELS,
    CONTROL_LEVELS,
    EVIDENCE_ROLES,
    EVIDENCE_SOURCE_TYPES,
    EVIDENCE_STRENGTHS,
    IMPORTANCE_LEVELS,
    MEASURE_VALIDITY_STATUSES,
    PROGRAM_TYPES,
    ensure_unique_slug,
    optional_text,
    parse_date,
    status_group,
    unset_other_active_programs,
)
from app.services.program_ai_workflow_service import (
    COMMITMENT_EVIDENCE_RELATION_TYPES,
    COMMITMENT_STATUS_TASK,
    PROGRAM_STRUCTURE_TASK,
    SECTION_BATCH_STATUS_TASK,
    SECTION_REFINEMENT_TASK,
    SECTION_SUMMARY_TASK,
    ai_run_context,
    build_section_batch_status_prompt,
    build_section_summary_prompt,
    create_or_update_ai_run,
    import_section_batch_status,
    import_section_summary,
    latest_ai_run,
    mark_import_failed,
    mark_parse_failed,
    mark_parse_success,
    parse_json,
    section_summary_readiness_error,
)
from app.services.program_analysis_batch_service import (
    batch_tranche_refs,
    refresh_batch_progress,
    section_analysis_batch_items,
)
from app.services.revision_service import create_entity_revision
from app.services.media_service import save_upload
from app.services.program_workflow_actions import (
    ProgramWorkflowError,
    approve_program_structure as workflow_approve_program_structure,
    generate_program_structure_prompt as workflow_generate_program_structure_prompt,
    generate_commitment_status_prompt as workflow_generate_commitment_status_prompt,
    generate_section_refinement_prompt as workflow_generate_section_refinement_prompt,
    import_commitment_status_json as workflow_import_commitment_status_json,
    import_program_structure_json as workflow_import_program_structure_json,
    import_section_refinement_json as workflow_import_section_refinement_json,
    publish_program as workflow_publish_program,
    start_section_status_batch as workflow_start_section_status_batch,
)

router = APIRouter(prefix="/internal/programs", tags=["internal-programs"], dependencies=[Depends(moderator_required)])

MAX_AI_JSON_FORM_BYTES = 16 * 1024 * 1024


def program_query():
    return select(Program).where(Program.is_deleted.is_(False)).options(selectinload(Program.related_party), selectinload(Program.sections)).order_by(
        Program.is_active_government_program.desc(),
        Program.created_at.desc(),
    )


def commitment_query():
    return (
        select(Commitment)
        .options(
            selectinload(Commitment.program),
            selectinload(Commitment.related_party),
            selectinload(Commitment.evidence_links).selectinload(CommitmentEvidence.evidence_item),
        )
        .order_by(Commitment.display_order, Commitment.created_at.desc())
    )


def form_options(db: Session) -> dict:
    return {
        "parties": db.scalars(select(PoliticalParty).where(PoliticalParty.is_deleted.is_(False)).order_by(PoliticalParty.full_name)).all(),
        "programs": db.scalars(select(Program).where(Program.is_deleted.is_(False)).order_by(Program.title)).all(),
        "sections": db.scalars(select(ProgramSection).order_by(ProgramSection.program_id, ProgramSection.display_order, ProgramSection.title)).all(),
        "program_types": PROGRAM_TYPES,
        "statuses": COMMITMENT_STATUSES,
        "confidence_levels": CONFIDENCE_LEVELS,
        "commitment_types": COMMITMENT_TYPES,
        "baseline_modes": BASELINE_MODES,
        "control_levels": CONTROL_LEVELS,
        "contribution_levels": CONTRIBUTION_LEVELS,
        "importance_levels": IMPORTANCE_LEVELS,
        "measure_validity_statuses": MEASURE_VALIDITY_STATUSES,
        "evidence_source_types": EVIDENCE_SOURCE_TYPES,
        "evidence_roles": EVIDENCE_ROLES,
        "evidence_strengths": EVIDENCE_STRENGTHS,
    }


def get_program(db: Session, program_id: UUID) -> Program:
    program = db.scalar(program_query().where(Program.id == program_id))
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


def get_commitment(db: Session, commitment_id: UUID) -> Commitment:
    commitment = db.scalar(commitment_query().where(Commitment.id == commitment_id))
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return commitment


def get_section(db: Session, section_id: UUID) -> ProgramSection:
    section = db.get(ProgramSection, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


def get_ai_run(
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
        raise HTTPException(status_code=404, detail="AI run not found")
    return ai_run


def ensure_ai_run_for_import(
    db: Session,
    ai_run_id: UUID | None,
    target_type: str,
    target_id: UUID,
    task_type: str,
    prompt_text: str,
    user: dict,
    run_context: dict | None = None,
) -> AiRun:
    if ai_run_id:
        ai_run = db.scalar(select(AiRun).where(AiRun.id == ai_run_id).with_for_update())
        if not ai_run or ai_run.target_type != target_type or ai_run.target_id != target_id or ai_run.task_type != task_type:
            raise HTTPException(status_code=404, detail="AI run not found")
    else:
        ai_run = get_ai_run(db, None, target_type, target_id, task_type)
        if ai_run:
            ai_run = db.scalar(select(AiRun).where(AiRun.id == ai_run.id).with_for_update())
    if not ai_run:
        ai_run = create_or_update_ai_run(db, target_type, target_id, task_type, prompt_text, user, **(run_context or {}))
        db.flush()
    return ai_run


def render_ai_json(
    request: Request,
    user: dict,
    program: Program,
    ai_run: AiRun | None,
    raw_json: str = "",
    status_code: int = 200,
    **context,
):
    return render(
        request,
        "internal/program_ai_json.html",
        {
            "user": user,
            "program": program,
            "ai_run": ai_run,
            "raw_json": raw_json,
            **context,
        },
        status_code=status_code,
    )


def store_ai_run_failure(
    db: Session,
    ai_run_id: UUID,
    raw_json: str,
    data: dict | None,
    error: str,
    user: dict,
) -> AiRun:
    db.rollback()
    ai_run = db.get(AiRun, ai_run_id)
    if data is None:
        mark_parse_failed(ai_run, raw_json, error, user)
    else:
        mark_import_failed(ai_run, raw_json, data, error, user)
    db.commit()
    return ai_run


def revise_program_structure(db: Session, program: Program, user: dict, note: str) -> None:
    db.flush()
    create_entity_revision(db, program, user, note)
    for section in db.scalars(select(ProgramSection).where(ProgramSection.program_id == program.id)):
        create_entity_revision(db, section, user, note)
    for commitment in db.scalars(select(Commitment).where(Commitment.program_id == program.id)):
        create_entity_revision(db, commitment, user, note)


def save_prompt_run(
    db: Session,
    ai_run_id: UUID | None,
    target_type: str,
    target_id: UUID,
    task_type: str,
    prompt_text: str,
    user: dict,
    run_context: dict,
) -> AiRun:
    ai_run = get_ai_run(db, ai_run_id, target_type, target_id, task_type) if ai_run_id else None
    if ai_run and ai_run.status == "prompt_generated" and not ai_run.raw_ai_response and not ai_run.parsed_json:
        ai_run.prompt_text = prompt_text
        return ai_run
    if ai_run:
        raise HTTPException(status_code=409, detail="This AI run is immutable after a response or import attempt. Generate a new prompt.")
    return create_or_update_ai_run(db, target_type, target_id, task_type, prompt_text, user, **run_context)


def preload_section_tree(sections: list[ProgramSection]) -> None:
    for section in sections:
        list(section.child_sections)
        list(section.commitments)


def section_commitment_totals(sections: list[ProgramSection]) -> dict[str, int]:
    totals: dict[str, int] = {}

    def total_for(section: ProgramSection) -> int:
        total = len(section.commitments)
        for child in section.child_sections:
            total += total_for(child)
        totals[str(section.id)] = total
        return total

    for section in sections:
        if not section.parent_section_id:
            total_for(section)
    return totals


def _required_text_field(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=422, detail=f"{field_name} is required")
    return value


def _optional_uuid_field(value: object) -> UUID | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise HTTPException(status_code=422, detail="ai_run_id must be a UUID")
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="ai_run_id must be a UUID") from exc


async def parse_ai_json_form(request: Request) -> tuple[str, UUID | None, str]:
    form = await request.form(max_part_size=MAX_AI_JSON_FORM_BYTES)
    raw_json = _required_text_field(form.get("raw_json"), "raw_json")
    if len(raw_json.encode("utf-8")) > MAX_AI_JSON_FORM_BYTES:
        raise HTTPException(status_code=413, detail=f"raw_json exceeded maximum size of {MAX_AI_JSON_FORM_BYTES // (1024 * 1024)}MB")
    ai_run_id = _optional_uuid_field(form.get("ai_run_id"))
    csrf_token = _required_text_field(form.get("csrf_token"), "csrf_token")
    validate_csrf(request, csrf_token)
    return raw_json, ai_run_id, csrf_token


@router.get("")
def programs(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    return render(
        request,
        "internal/programs.html",
        {"user": user, "programs": db.scalars(program_query()).all(), "program_types": PROGRAM_TYPES},
    )


@router.get("/new")
def new_program(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    context = {
        "user": user,
        "program": None,
        "form_action": "/internal/programs",
        "form_title": "New program - step 1 of 4: draft details",
        "form_note": "Add the basic program information. The program is not published from here.",
        "submit_label": "Next",
        "show_publish_controls": False,
    }
    context.update(form_options(db))
    return render(request, "internal/program_form.html", context)


@router.post("")
def create_program(
    request: Request,
    title: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    program_type: str = Form("other"),
    political_subject_name: str = Form(...),
    related_party_id: str = Form(""),
    related_coalition_name: str = Form(""),
    period_text: str = Form(""),
    period_start: str = Form(""),
    period_end: str = Form(""),
    publication_date: str = Form(""),
    source_url: str = Form(""),
    source_title: str = Form(""),
    source_description: str = Form(""),
    internal_notes: str = Form(""),
    is_active_government_program: str | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    active = bool(is_active_government_program)
    program = Program(
        title=title.strip(),
        slug=ensure_unique_slug(db, Program, slug or title),
        description=optional_text(description),
        program_type=program_type if program_type in PROGRAM_TYPES else "other",
        political_subject_name=political_subject_name.strip(),
        related_party_id=related_party_id or None,
        related_coalition_name=optional_text(related_coalition_name),
        period_text=optional_text(period_text),
        period_start=parse_date(period_start),
        period_end=parse_date(period_end),
        publication_date=parse_date(publication_date),
        source_url=optional_text(source_url),
        source_title=optional_text(source_title),
        source_description=optional_text(source_description),
        internal_notes=optional_text(internal_notes),
        is_active_government_program=active,
        is_published=False,
    )
    if active:
        unset_other_active_programs(db)
    db.add(program)
    db.flush()
    create_entity_revision(db, program, user, "program_created")
    db.commit()
    write_audit_log(db, request, user, "create_program", "program", str(program.id), {"slug": program.slug})
    return RedirectResponse(f"/internal/programs/{program.id}/prompt", status_code=303)


@router.get("/{program_id}/prompt")
def program_prompt(program_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    program = get_program(db, program_id)
    prompt_note = (
        "Ако е въведен текст на програмата, AI ще извлече структурата от него. "
        "Ако има посочен източник/URL, AI първо ще използва него. "
        "Ако няма източник, AI трябва сам да намери официалната програма чрез публично търсене. "
        "Използвайте този prompt само с AI модел с достъп до интернет / browsing / deep research, когато не подавате пълен текст."
    )
    try:
        result = workflow_generate_program_structure_prompt(db, program_id, user)
    except ProgramWorkflowError as exc:
        return render(
            request,
            "internal/program_prompt.html",
            {
                "user": user,
                "program": program,
                "prompt": "",
                "error": exc.message,
                "prompt_title": "Program structure extraction prompt",
                "prompt_note": prompt_note,
            },
            status_code=exc.status_code,
        )
    write_audit_log(db, request, user, "generate_program_structure_prompt", "program", str(program.id), {"ai_run_id": str(result.ai_run.id)})
    return render(
        request,
        "internal/program_prompt.html",
        {
            "user": user,
            "program": program,
            "ai_run": result.ai_run,
            "prompt": result.prompt,
            "prompt_title": "Program structure extraction prompt",
            "prompt_note": prompt_note,
        },
    )


@router.post("/{program_id}/prompt")
def save_program_prompt(
    program_id: UUID,
    request: Request,
    prompt_text: str = Form(...),
    ai_run_id: UUID | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    program = get_program(db, program_id)
    ai_run = save_prompt_run(
        db, ai_run_id, "program", program.id, PROGRAM_STRUCTURE_TASK, prompt_text, user, ai_run_context(program, PROGRAM_STRUCTURE_TASK)
    )
    db.commit()
    write_audit_log(db, request, user, "save_program_ai_prompt", "program", str(program.id), {"ai_run_id": str(ai_run.id)})
    return RedirectResponse(f"/internal/programs/{program.id}/ai-json?ai_run_id={ai_run.id}", status_code=303)


@router.get("/{program_id}/ai-json")
def program_ai_json_form(
    program_id: UUID,
    request: Request,
    ai_run_id: UUID | None = Query(default=None),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    program = get_program(db, program_id)
    ai_run = get_ai_run(db, ai_run_id, "program", program.id, PROGRAM_STRUCTURE_TASK)
    return render_ai_json(request, user, program, ai_run, ai_run.raw_ai_response if ai_run else "")


@router.post("/{program_id}/ai-json")
async def save_program_ai_json(
    program_id: UUID,
    request: Request,
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    raw_json, ai_run_id, _ = await parse_ai_json_form(request)
    program = get_program(db, program_id)
    try:
        result = workflow_import_program_structure_json(db, program_id, raw_json, ai_run_id, user)
    except ProgramWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if not result.ok:
        action = {
            "source_retrieval_failed": "program_structure_no_import",
            "parse_failed": "program_structure_parse_failed",
        }.get(result.error_kind, "program_structure_import_failed")
        write_audit_log(db, request, user, action, "program", str(program.id), {"error": result.error, "ai_run_id": str(result.ai_run.id)})
        return render_ai_json(
            request,
            user,
            program,
            result.ai_run,
            raw_json,
            error=result.error,
            status_code=result.status_code,
        )
    write_audit_log(db, request, user, "import_program_structure", "program", str(program.id), {"imported_count": result.imported_count})
    return RedirectResponse(f"/internal/programs/{program.id}/preview", status_code=303)


@router.get("/{program_id}/preview")
def program_preview(program_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    program = get_program(db, program_id)
    commitments = db.scalars(commitment_query().where(Commitment.program_id == program.id)).all()
    preload_section_tree(list(program.sections))
    root_sections = sorted(
        [section for section in program.sections if not section.parent_section_id],
        key=lambda section: (section.display_order, section.title),
    )
    unsectioned_commitments = sorted(
        [commitment for commitment in commitments if not commitment.program_section_id],
        key=lambda commitment: (commitment.display_order, commitment.title),
    )
    commitment_totals = section_commitment_totals(list(program.sections))
    target_ids = [program.id, *(section.id for section in program.sections), *(commitment.id for commitment in commitments)]
    ai_runs = db.scalars(select(AiRun).where(AiRun.target_id.in_(target_ids)).order_by(AiRun.created_at.desc()).limit(100)).all()
    return render(
        request,
        "internal/program_preview.html",
        {
            "user": user,
            "program": program,
            "root_sections": root_sections,
            "section_commitment_totals": commitment_totals,
            "commitments": commitments,
            "unsectioned_commitments": unsectioned_commitments,
            "ai_runs": ai_runs,
            "statuses": COMMITMENT_STATUSES,
            "confidence_levels": CONFIDENCE_LEVELS,
            "contribution_levels": CONTRIBUTION_LEVELS,
        },
    )


@router.post("/{program_id}/documents")
async def upload_program_document(
    program_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    program = get_program(db, program_id)
    if not file.filename:
        raise HTTPException(status_code=400, detail="A document filename is required")
    file_path, original_filename = await save_upload(file)
    asset = MediaAsset(
        file_path=file_path,
        media_type="program_source_document",
        original_filename=original_filename,
        mime_type=file.content_type,
        created_by_user_id=user.get("moderator").id if user.get("moderator") else None,
    )
    db.add(asset)
    db.flush()
    program.media.append(asset)
    create_entity_revision(db, program, user, "program_document_attached")
    db.commit()
    write_audit_log(db, request, user, "attach_program_document", "program", str(program.id), {"filename": original_filename})
    return RedirectResponse(f"/internal/programs/{program.id}/preview", status_code=303)


@router.post("/{program_id}/publish")
def publish_program(
    program_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    try:
        result = workflow_publish_program(db, program_id, user)
    except ProgramWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    write_audit_log(db, request, user, "publish_program", "program", str(result.program.id), {"commitment_count": result.commitment_count})
    return RedirectResponse("/internal/programs", status_code=303)


@router.post("/{program_id}/structural-review")
def structural_review_program(
    program_id: UUID,
    request: Request,
    structural_review_status: str = Form(...),
    structural_review_note: str = Form(""),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    try:
        result = workflow_approve_program_structure(db, program_id, structural_review_status, structural_review_note, user)
    except ProgramWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    write_audit_log(db, request, user, "program_structural_review", "program", str(result.program.id), {"status": structural_review_status})
    return RedirectResponse(f"/internal/programs/{result.program.id}/preview", status_code=303)


@router.get("/{program_id}/edit")
def edit_program(program_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    context = {
        "user": user,
        "program": get_program(db, program_id),
        "form_action": f"/internal/programs/{program_id}/edit",
        "form_title": "Edit program",
        "form_note": "Update program details. Publishing happens from the preview step.",
        "submit_label": "Save changes",
        "show_publish_controls": True,
    }
    context.update(form_options(db))
    return render(request, "internal/program_form.html", context)


@router.post("/{program_id}/edit")
def update_program(
    program_id: UUID,
    request: Request,
    title: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    program_type: str = Form("other"),
    political_subject_name: str = Form(...),
    related_party_id: str = Form(""),
    related_coalition_name: str = Form(""),
    period_start: str = Form(""),
    period_end: str = Form(""),
    period_text: str = Form(""),
    publication_date: str = Form(""),
    source_url: str = Form(""),
    source_title: str = Form(""),
    source_description: str = Form(""),
    internal_notes: str = Form(""),
    is_active_government_program: str | None = Form(None),
    is_published: str | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    program = get_program(db, program_id)
    active = bool(is_active_government_program)
    if active:
        unset_other_active_programs(db, program)
    program.title = title.strip()
    program.slug = ensure_unique_slug(db, Program, slug or title, program.id)
    program.description = optional_text(description)
    program.program_type = program_type if program_type in PROGRAM_TYPES else "other"
    program.political_subject_name = political_subject_name.strip()
    program.related_party_id = related_party_id or None
    program.related_coalition_name = optional_text(related_coalition_name)
    program.period_text = optional_text(period_text)
    program.period_start = parse_date(period_start)
    program.period_end = parse_date(period_end)
    program.publication_date = parse_date(publication_date)
    program.source_url = optional_text(source_url)
    program.source_title = optional_text(source_title)
    program.source_description = optional_text(source_description)
    program.internal_notes = optional_text(internal_notes)
    program.is_active_government_program = active
    requested_published = bool(is_published)
    if requested_published and program.structural_review_status != "passed":
        raise HTTPException(status_code=409, detail="The program must pass structural review before publication.")
    program.is_published = requested_published
    if requested_published:
        program.status = "published"
        commitments = db.scalars(select(Commitment).where(Commitment.program_id == program.id)).all()
        for commitment in commitments:
            commitment.is_published = True
    create_entity_revision(db, program, user, "program_updated")
    db.commit()
    write_audit_log(db, request, user, "update_program", "program", str(program.id), {"slug": program.slug})
    return RedirectResponse("/internal/programs", status_code=303)


@router.post("/{program_id}/unpublish")
def unpublish_program(
    program_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    program = get_program(db, program_id)
    program.is_published = False
    program.is_active_government_program = False
    db.commit()
    write_audit_log(db, request, user, "unpublish_program", "program", str(program.id))
    return RedirectResponse("/internal/programs", status_code=303)


@router.post("/{program_id}/delete")
def delete_program(
    program_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(root_admin_required),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    program = db.get(Program, program_id)
    if program and not program.is_deleted:
        program.is_deleted = True
        program.is_published = False
        program.is_active_government_program = False
        commitments = db.scalars(select(Commitment).where(Commitment.program_id == program.id)).all()
        for commitment in commitments:
            commitment.is_published = False
        db.commit()
        write_audit_log(db, request, user, "delete_program", "program", str(program.id), {"title": program.title})
    return RedirectResponse("/internal/programs", status_code=303)


@router.get("/sections/new")
def new_section(
    request: Request,
    program_id: UUID = Query(...),
    parent_section_id: UUID | None = Query(default=None),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    program = get_program(db, program_id)
    return render(
        request,
        "internal/program_section_form.html",
        {
            "user": user,
            "section": None,
            "program": program,
            "parent_section_id": parent_section_id,
            "parent_options": sorted(program.sections, key=lambda item: (item.display_order, item.title)),
            "form_action": "/internal/programs/sections",
        },
    )


@router.post("/sections")
def create_section(
    request: Request,
    program_id: UUID = Form(...),
    parent_section_id: UUID | None = Form(None),
    section_code: str = Form(""),
    title: str = Form(...),
    original_heading: str = Form(""),
    original_text: str = Form(""),
    summary: str = Form(""),
    problem_description: str = Form(""),
    policy_area: str = Form(""),
    display_order: int = Form(0),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    program = get_program(db, program_id)
    if parent_section_id:
        parent = get_section(db, parent_section_id)
        if parent.program_id != program.id:
            raise HTTPException(status_code=400, detail="Parent section belongs to another program")
    section = ProgramSection(
        program_id=program.id,
        parent_section_id=parent_section_id,
        section_code=optional_text(section_code),
        title=title.strip(),
        slug=ensure_unique_slug(db, ProgramSection, section_code or title),
        original_heading=optional_text(original_heading),
        original_text=optional_text(original_text),
        summary=optional_text(summary),
        problem_description=optional_text(problem_description),
        policy_area=optional_text(policy_area),
        display_order=display_order,
        source_origin="manual",
        structural_status="draft",
        factual_review_status="not_reviewed",
    )
    db.add(section)
    db.flush()
    create_entity_revision(db, section, user, "section_created")
    db.commit()
    write_audit_log(db, request, user, "create_program_section", "program_section", str(section.id), {"title": section.title})
    return RedirectResponse(f"/internal/programs/{program.id}/preview", status_code=303)


@router.get("/sections/{section_id}/edit")
def edit_section(section_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    section = get_section(db, section_id)
    return render(
        request,
        "internal/program_section_form.html",
        {
            "user": user,
            "section": section,
            "program": section.program,
            "parent_section_id": section.parent_section_id,
            "parent_options": [item for item in section.program.sections if item.id != section.id],
            "form_action": f"/internal/programs/sections/{section.id}/edit",
        },
    )


@router.post("/sections/{section_id}/edit")
def update_section(
    section_id: UUID,
    request: Request,
    parent_section_id: UUID | None = Form(None),
    section_code: str = Form(""),
    title: str = Form(...),
    original_heading: str = Form(""),
    original_text: str = Form(""),
    summary: str = Form(""),
    problem_description: str = Form(""),
    aggregate_status_summary: str = Form(""),
    policy_area: str = Form(""),
    display_order: int = Form(0),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    section = get_section(db, section_id)
    if parent_section_id:
        parent = get_section(db, parent_section_id)
        if parent.program_id != section.program_id or parent.id == section.id:
            raise HTTPException(status_code=400, detail="Invalid parent section")
        ancestor = parent
        while ancestor:
            if ancestor.id == section.id:
                raise HTTPException(status_code=400, detail="Section hierarchy cannot contain a cycle")
            ancestor = ancestor.parent_section
    section.parent_section_id = parent_section_id
    section.section_code = optional_text(section_code)
    section.title = title.strip()
    section.original_heading = optional_text(original_heading)
    section.original_text = optional_text(original_text)
    section.summary = optional_text(summary)
    section.problem_description = optional_text(problem_description)
    section.aggregate_status_summary = optional_text(aggregate_status_summary)
    section.policy_area = optional_text(policy_area)
    section.display_order = display_order
    create_entity_revision(db, section, user, "section_updated")
    db.commit()
    write_audit_log(db, request, user, "update_program_section", "program_section", str(section.id), {"title": section.title})
    return RedirectResponse(f"/internal/programs/{section.program_id}/preview", status_code=303)


@router.post("/sections/{section_id}/delete")
def delete_section(
    section_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    section = get_section(db, section_id)
    program_id = section.program_id
    if section.program.is_published:
        raise HTTPException(status_code=409, detail="Unpublish the program before deleting structure")
    if section.commitments or section.child_sections:
        raise HTTPException(status_code=409, detail="Move or delete child sections and commitments first")
    title = section.title
    create_entity_revision(db, section, user, "section_deleted")
    db.delete(section)
    db.commit()
    write_audit_log(db, request, user, "delete_program_section", "program_section", str(section_id), {"title": title})
    return RedirectResponse(f"/internal/programs/{program_id}/preview", status_code=303)


@router.get("/sections/{section_id}/refinement-prompt")
def section_refinement_prompt(section_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    section = get_section(db, section_id)
    try:
        result = workflow_generate_section_refinement_prompt(db, section_id, user)
    except ProgramWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    write_audit_log(db, request, user, "generate_section_refinement_prompt", "program_section", str(section.id), {"ai_run_id": str(result.ai_run.id)})
    return render(
        request,
        "internal/program_prompt.html",
        {
            "user": user,
            "program": section.program,
            "ai_run": result.ai_run,
            "prompt": result.prompt,
            "heading": section.title,
            "prompt_title": "Section structure refinement prompt",
            "prompt_note": "Copy this prompt into an external AI model. It can add child sections and candidate commitments, but must not analyze implementation status.",
            "form_action": f"/internal/programs/sections/{section.id}/refinement-prompt",
        },
    )


@router.post("/sections/{section_id}/refinement-prompt")
def save_section_refinement_prompt(
    section_id: UUID,
    request: Request,
    prompt_text: str = Form(...),
    ai_run_id: UUID | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    section = get_section(db, section_id)
    ai_run = save_prompt_run(
        db,
        ai_run_id,
        "program_section",
        section.id,
        SECTION_REFINEMENT_TASK,
        prompt_text,
        user,
        ai_run_context(section, SECTION_REFINEMENT_TASK),
    )
    db.commit()
    write_audit_log(db, request, user, "save_section_refinement_prompt", "program_section", str(section.id), {"ai_run_id": str(ai_run.id)})
    return RedirectResponse(f"/internal/programs/sections/{section.id}/refinement-json?ai_run_id={ai_run.id}", status_code=303)


@router.get("/sections/{section_id}/refinement-json")
def section_refinement_json_form(
    section_id: UUID,
    request: Request,
    ai_run_id: UUID | None = Query(default=None),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    section = get_section(db, section_id)
    ai_run = get_ai_run(db, ai_run_id, "program_section", section.id, SECTION_REFINEMENT_TASK)
    return render_ai_json(
        request,
        user,
        section.program,
        ai_run,
        ai_run.raw_ai_response if ai_run else "",
        heading=section.title,
        json_title="Import section refinement JSON",
        json_note="This imports child sections and candidate commitments only. It does not analyze implementation status.",
        form_action=f"/internal/programs/sections/{section.id}/refinement-json",
    )


@router.post("/sections/{section_id}/refinement-json")
async def save_section_refinement_json(
    section_id: UUID,
    request: Request,
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    raw_json, ai_run_id, _ = await parse_ai_json_form(request)
    section = get_section(db, section_id)
    try:
        result = workflow_import_section_refinement_json(db, section_id, raw_json, ai_run_id, user)
    except ProgramWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if not result.ok:
        write_audit_log(db, request, user, "section_refinement_import_failed", "program_section", str(section.id), {"error": result.error})
        return render_ai_json(
            request,
            user,
            section.program,
            result.ai_run,
            raw_json,
            error=result.error,
            heading=section.title,
            json_title="Import section refinement JSON",
            form_action=f"/internal/programs/sections/{section.id}/refinement-json",
            status_code=result.status_code,
        )
    write_audit_log(db, request, user, "import_section_refinement", "program_section", str(section.id), {"imported_count": result.imported_count})
    return RedirectResponse(f"/internal/programs/{section.program_id}/preview", status_code=303)


@router.get("/sections/{section_id}/batch-status")
def section_status_batch_workspace(
    section_id: UUID,
    request: Request,
    scope: str = Query(default="recursive"),
    batch_id: UUID | None = Query(default=None),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    if scope not in {"direct", "recursive"}:
        raise HTTPException(status_code=400, detail="scope must be direct or recursive")
    suffix = f"&ai_run_id={batch_id}" if batch_id else ""
    return RedirectResponse(
        f"/internal/programs/sections/{section_id}/batch-status-prompt?scope={scope}{suffix}",
        status_code=303,
    )


@router.get("/sections/{section_id}/batch-status-prompt")
def section_batch_status_prompt(
    section_id: UUID,
    request: Request,
    scope: str = Query(default="recursive"),
    ai_run_id: UUID | None = Query(default=None),
    tranche_size: int = Query(default=50, ge=1, le=100),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    normalized_scope = "direct" if scope == "direct" else "recursive"
    section = get_section(db, section_id)
    if ai_run_id:
        ai_run = get_ai_run(db, ai_run_id, "program_section", section.id, SECTION_BATCH_STATUS_TASK)
        if not ai_run:
            raise HTTPException(status_code=404, detail="AI batch run not found")
    else:
        try:
            result = workflow_start_section_status_batch(
                db,
                section_id,
                user,
                recursive=normalized_scope == "recursive",
                tranche_size=tranche_size,
            )
        except ProgramWorkflowError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        ai_run = result.batch
        write_audit_log(
            db,
            request,
            user,
            "start_section_status_batch",
            "program_section",
            str(section_id),
            {"batch_id": str(ai_run.id), "scope": normalized_scope, "commitment_count": ai_run.expected_item_count},
        )
    items = section_analysis_batch_items(db, ai_run.id)
    saved_snapshot = ai_run.input_snapshot or {}
    effective_size = int(saved_snapshot.get("tranche_size") or tranche_size or 50)
    current_refs = batch_tranche_refs(items, tranche_size=effective_size)
    if not current_refs:
        refresh_batch_progress(db, ai_run)
        db.commit()
        return RedirectResponse(f"/internal/programs/{section.program_id}/preview", status_code=303)
    ai_run.input_snapshot = {
        **saved_snapshot,
        "scope": normalized_scope,
        "tranche_size": effective_size,
        "current_tranche_refs": current_refs,
    }
    ai_run.prompt_text = build_section_batch_status_prompt(
        section,
        recursive=normalized_scope == "recursive",
        commitment_refs=current_refs,
    )
    if ai_run.status not in {"completed", "imported"}:
        ai_run.status = "in_progress"
    progress = refresh_batch_progress(db, ai_run)
    db.commit()
    return render(
        request,
        "internal/program_prompt.html",
        {
            "user": user,
            "program": section.program,
            "ai_run": ai_run,
            "prompt": ai_run.prompt_text,
            "heading": section.title,
            "prompt_title": "Batch commitment analysis prompt",
            "prompt_note": (
                f"Tranche {progress['completed_item_count'] + 1}-{min(progress['completed_item_count'] + len(current_refs), progress['expected_item_count'])} "
                f"of {progress['expected_item_count']}. Save this prompt, run it externally, then paste the JSON response."
            ),
            "form_action": f"/internal/programs/sections/{section.id}/batch-status-prompt",
            "scope": normalized_scope,
        },
    )


@router.post("/sections/{section_id}/batch-status-prompt")
def save_section_batch_status_prompt(
    section_id: UUID,
    request: Request,
    prompt_text: str = Form(...),
    ai_run_id: UUID | None = Form(None),
    scope: str = Form("recursive"),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    section = get_section(db, section_id)
    recursive = scope != "direct"
    if not ai_run_id:
        raise HTTPException(status_code=400, detail="Missing AI batch run")
    ai_run = get_ai_run(db, ai_run_id, "program_section", section.id, SECTION_BATCH_STATUS_TASK)
    if not ai_run:
        raise HTTPException(status_code=404, detail="AI batch run not found")
    if ai_run.status in {"completed", "imported"}:
        raise HTTPException(status_code=409, detail="This batch is already complete.")
    ai_run.prompt_text = prompt_text
    ai_run.status = "in_progress"
    ai_run.input_snapshot = {
        **(ai_run.input_snapshot or {}),
        "scope": "recursive" if recursive else "direct",
    }
    db.commit()
    write_audit_log(db, request, user, "save_section_batch_status_prompt", "program_section", str(section.id), {"ai_run_id": str(ai_run.id)})
    return RedirectResponse(f"/internal/programs/sections/{section.id}/batch-status-json?ai_run_id={ai_run.id}", status_code=303)


@router.get("/sections/{section_id}/batch-status-json")
def section_batch_status_json_form(
    section_id: UUID,
    request: Request,
    ai_run_id: UUID | None = Query(default=None),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    section = get_section(db, section_id)
    ai_run = get_ai_run(db, ai_run_id, "program_section", section.id, SECTION_BATCH_STATUS_TASK)
    return render_ai_json(
        request,
        user,
        section.program,
        ai_run,
        ai_run.raw_ai_response if ai_run else "",
        heading=section.title,
        json_title="Import batch commitment analysis JSON",
        json_note="This updates individual commitments and may update section summaries. The section itself does not receive a status.",
        form_action=f"/internal/programs/sections/{section.id}/batch-status-json",
    )


@router.post("/sections/{section_id}/batch-status-json")
async def save_section_batch_status_json(
    section_id: UUID,
    request: Request,
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    raw_json, ai_run_id, _ = await parse_ai_json_form(request)
    section = get_section(db, section_id)
    ai_run = get_ai_run(db, ai_run_id, "program_section", section.id, SECTION_BATCH_STATUS_TASK)
    if not ai_run:
        raise HTTPException(status_code=404, detail="AI batch run not found")
    if ai_run.status in {"completed", "imported"}:
        return render_ai_json(
            request,
            user,
            section.program,
            ai_run,
            raw_json,
            error="This AI run has already been imported. Generate a new prompt before importing again.",
            heading=section.title,
            json_title="Import batch commitment analysis JSON",
            form_action=f"/internal/programs/sections/{section.id}/batch-status-json",
            status_code=409,
        )
    data = None
    try:
        data = parse_json(raw_json)
        current_refs = set((ai_run.input_snapshot or {}).get("current_tranche_refs") or [])
        if not current_refs:
            raise ValueError("No pending tranche is stored for this batch. Generate the next batch prompt first.")
        imported_count = import_section_batch_status(db, section, data, ai_run, user, expected_commitment_refs=current_refs)
        now = datetime.now(timezone.utc)
        ai_run.raw_ai_response = raw_json
        previous_payload = ai_run.parsed_json if isinstance(ai_run.parsed_json, dict) else {}
        tranche_responses = list(previous_payload.get("tranche_responses") or [])
        tranche_responses.append({"refs": sorted(current_refs), "response": data, "imported_at": now.isoformat()})
        ai_run.parsed_json = {"tranche_responses": tranche_responses, "last_response": data}
        ai_run.parse_error = None
        ai_run.import_error = None
        ai_run.response_pasted_at = now
        ai_run.response_pasted_by_user_id = user.get("moderator").id if user.get("moderator") else None
        ai_run.parsed_at = now
        ai_run.validated_at = now
        refresh_batch_progress(db, ai_run)
        items = section_analysis_batch_items(db, ai_run.id)
        next_refs = batch_tranche_refs(items, tranche_size=int((ai_run.input_snapshot or {}).get("tranche_size") or 50))
        ai_run.input_snapshot = {
            **(ai_run.input_snapshot or {}),
            "completed_commitment_refs": [
                item.batch_item_ref for item in items if item.status == "imported" and item.batch_item_ref
            ],
            "current_tranche_refs": next_refs,
        }
        if next_refs:
            ai_run.prompt_text = build_section_batch_status_prompt(
                section,
                recursive=(ai_run.input_snapshot or {}).get("scope") != "direct",
                commitment_refs=next_refs,
            )
            ai_run.status = "in_progress"
        else:
            ai_run.status = "completed"
            ai_run.imported_at = now
        revise_program_structure(db, section.program, user, "section_batch_status_imported")
    except (ValueError, SQLAlchemyError) as exc:
        error = str(exc) if isinstance(exc, ValueError) else "The validated batch could not be saved atomically. No commitment analyses were imported."
        ai_run = store_ai_run_failure(db, ai_run.id, raw_json, data, error, user)
        section = get_section(db, section_id)
        write_audit_log(db, request, user, "section_batch_status_import_failed", "program_section", str(section.id), {"error": error})
        return render_ai_json(
            request,
            user,
            section.program,
            ai_run,
            raw_json,
            error=error,
            heading=section.title,
            json_title="Import batch commitment analysis JSON",
            form_action=f"/internal/programs/sections/{section.id}/batch-status-json",
            status_code=400,
        )
    db.commit()
    write_audit_log(db, request, user, "import_section_batch_status", "program_section", str(section.id), {"commitment_count": imported_count})
    if next_refs:
        return RedirectResponse(
            f"/internal/programs/sections/{section.id}/batch-status-prompt?ai_run_id={ai_run.id}&scope={(ai_run.input_snapshot or {}).get('scope', 'recursive')}",
            status_code=303,
        )
    return RedirectResponse(f"/internal/programs/{section.program_id}/preview", status_code=303)


@router.get("/sections/{section_id}/summary-prompt")
def section_summary_prompt(section_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    section = get_section(db, section_id)
    readiness_error = section_summary_readiness_error(section)
    if readiness_error:
        raise HTTPException(status_code=409, detail=readiness_error)
    prompt = build_section_summary_prompt(section)
    ai_run = create_or_update_ai_run(
        db, "program_section", section.id, SECTION_SUMMARY_TASK, prompt, user, **ai_run_context(section, SECTION_SUMMARY_TASK)
    )
    db.commit()
    write_audit_log(db, request, user, "generate_section_summary_prompt", "program_section", str(section.id), {"ai_run_id": str(ai_run.id)})
    return render(
        request,
        "internal/program_prompt.html",
        {
            "user": user,
            "program": section.program,
            "ai_run": ai_run,
            "prompt": prompt,
            "heading": section.title,
            "prompt_title": "Section summary prompt",
            "prompt_note": "Copy this prompt into an external AI model. It updates narrative section fields only.",
            "form_action": f"/internal/programs/sections/{section.id}/summary-prompt",
        },
    )


@router.post("/sections/{section_id}/summary-prompt")
def save_section_summary_prompt(
    section_id: UUID,
    request: Request,
    prompt_text: str = Form(...),
    ai_run_id: UUID | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    section = get_section(db, section_id)
    ai_run = save_prompt_run(
        db,
        ai_run_id,
        "program_section",
        section.id,
        SECTION_SUMMARY_TASK,
        prompt_text,
        user,
        ai_run_context(section, SECTION_SUMMARY_TASK),
    )
    db.commit()
    write_audit_log(db, request, user, "save_section_summary_prompt", "program_section", str(section.id), {"ai_run_id": str(ai_run.id)})
    return RedirectResponse(f"/internal/programs/sections/{section.id}/summary-json?ai_run_id={ai_run.id}", status_code=303)


@router.get("/sections/{section_id}/summary-json")
def section_summary_json_form(
    section_id: UUID,
    request: Request,
    ai_run_id: UUID | None = Query(default=None),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    section = get_section(db, section_id)
    ai_run = get_ai_run(db, ai_run_id, "program_section", section.id, SECTION_SUMMARY_TASK)
    return render_ai_json(
        request,
        user,
        section.program,
        ai_run,
        ai_run.raw_ai_response if ai_run else "",
        heading=section.title,
        json_title="Import section summary JSON",
        json_note="This updates summary/problem/aggregate fields only. It does not update commitment statuses.",
        form_action=f"/internal/programs/sections/{section.id}/summary-json",
    )


@router.post("/sections/{section_id}/summary-json")
async def save_section_summary_json(
    section_id: UUID,
    request: Request,
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    raw_json, ai_run_id, _ = await parse_ai_json_form(request)
    section = get_section(db, section_id)
    readiness_error = section_summary_readiness_error(section)
    if readiness_error:
        raise HTTPException(status_code=409, detail=readiness_error)
    ai_run = ensure_ai_run_for_import(
        db,
        ai_run_id,
        "program_section",
        section.id,
        SECTION_SUMMARY_TASK,
        build_section_summary_prompt(section),
        user,
        ai_run_context(section, SECTION_SUMMARY_TASK),
    )
    if ai_run.status == "imported":
        return render_ai_json(
            request,
            user,
            section.program,
            ai_run,
            raw_json,
            error="This AI run has already been imported. Generate a new prompt before importing again.",
            heading=section.title,
            json_title="Import section summary JSON",
            form_action=f"/internal/programs/sections/{section.id}/summary-json",
            status_code=409,
        )
    data = None
    try:
        data = parse_json(raw_json)
        import_section_summary(db, section, data, ai_run)
        mark_parse_success(ai_run, raw_json, data, user)
        create_entity_revision(db, section, user, "section_summary_imported")
    except (ValueError, SQLAlchemyError) as exc:
        error = str(exc) if isinstance(exc, ValueError) else "The validated section summary could not be saved."
        ai_run = store_ai_run_failure(db, ai_run.id, raw_json, data, error, user)
        section = get_section(db, section_id)
        write_audit_log(db, request, user, "section_summary_import_failed", "program_section", str(section.id), {"error": error})
        return render_ai_json(
            request,
            user,
            section.program,
            ai_run,
            raw_json,
            error=error,
            heading=section.title,
            json_title="Import section summary JSON",
            form_action=f"/internal/programs/sections/{section.id}/summary-json",
            status_code=400,
        )
    db.commit()
    write_audit_log(db, request, user, "import_section_summary", "program_section", str(section.id), {"ai_run_id": str(ai_run.id)})
    return RedirectResponse(f"/internal/programs/{section.program_id}/preview", status_code=303)


@router.get("/commitments")
def commitments(
    request: Request,
    program_id: str = "",
    status: str = "",
    topic: str = "",
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    query = commitment_query()
    if program_id:
        query = query.where(Commitment.program_id == program_id)
    if status:
        query = query.where(Commitment.current_status == status)
    if topic:
        query = query.where(Commitment.topic.ilike(f"%{topic}%"))
    context = {
        "user": user,
        "commitments": db.scalars(query).all(),
        "selected_program_id": program_id,
        "selected_status": status,
        "topic": topic,
    }
    context.update(form_options(db))
    return render(request, "internal/commitments.html", context)


@router.get("/commitments/new")
def new_commitment(request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    context = {"user": user, "commitment": None, "form_action": "/internal/programs/commitments", "form_title": "New commitment"}
    context.update(form_options(db))
    return render(request, "internal/commitment_form.html", context)


@router.post("/commitments")
def create_commitment(
    request: Request,
    program_id: str = Form(...),
    program_section_id: str = Form(""),
    title: str = Form(...),
    slug: str = Form(""),
    original_text: str = Form(...),
    normalized_description: str = Form(""),
    political_subject_name: str = Form(""),
    related_party_id: str = Form(""),
    related_coalition_name: str = Form(""),
    topic: str = Form(""),
    responsible_institutions: str = Form(""),
    period: str = Form(""),
    deadline: str = Form(""),
    measurable_criteria: str = Form(""),
    commitment_type: str = Form(""),
    promised_item_type: str = Form(""),
    baseline_mode: str = Form(""),
    required_external_actors: str = Form(""),
    control_level: str = Form(""),
    evaluation_basis: str = Form(""),
    contribution_types: str = Form(""),
    official_program_change_note: str = Form(""),
    source_version_note: str = Form(""),
    quantitative_target: str = Form(""),
    quantitative_actual: str = Form(""),
    measure_validity_status: str = Form(""),
    status: str = Form("not_analyzed"),
    status_explanation: str = Form(""),
    confidence_level: str = Form("medium"),
    confidence_explanation: str = Form(""),
    contribution_level: str = Form("indeterminate"),
    contribution_explanation: str = Form(""),
    contribution_confidence: str = Form(""),
    importance_level: str = Form("standard"),
    importance_weight: int = Form(2),
    last_status_update: str = Form(""),
    is_key_commitment: str | None = Form(None),
    display_order: int = Form(0),
    is_published: str | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    if program_section_id:
        selected_section = db.get(ProgramSection, program_section_id)
        if not selected_section or str(selected_section.program_id) != program_id:
            raise HTTPException(status_code=400, detail="Selected section belongs to another program")
    commitment = Commitment(
        program_id=program_id,
        program_section_id=program_section_id or None,
        title=title.strip(),
        slug=ensure_unique_slug(db, Commitment, slug or title),
        original_text=original_text.strip(),
        normalized_description=optional_text(normalized_description),
        political_subject_name=optional_text(political_subject_name),
        related_party_id=related_party_id or None,
        related_coalition_name=optional_text(related_coalition_name),
        topic=optional_text(topic),
        responsible_institutions=optional_text(responsible_institutions),
        period=optional_text(period),
        deadline=parse_date(deadline),
        measurable_criteria=optional_text(measurable_criteria),
        commitment_type=commitment_type if commitment_type in COMMITMENT_TYPES else None,
        promised_item_type=promised_item_type if promised_item_type in COMMITMENT_TYPES else None,
        baseline_mode=baseline_mode if baseline_mode in BASELINE_MODES else None,
        required_external_actors=optional_text(required_external_actors),
        control_level=control_level if control_level in CONTROL_LEVELS else None,
        evaluation_basis=optional_text(evaluation_basis),
        contribution_types_text=optional_text(contribution_types),
        official_program_change_note=optional_text(official_program_change_note),
        source_version_note=optional_text(source_version_note),
        quantitative_target=optional_text(quantitative_target),
        quantitative_actual=optional_text(quantitative_actual),
        measure_validity_status=measure_validity_status if measure_validity_status in MEASURE_VALIDITY_STATUSES else None,
        status=status if status in COMMITMENT_STATUSES else "not_analyzed",
        status_group=status_group(status),
        status_explanation=optional_text(status_explanation),
        confidence_level=confidence_level if confidence_level in CONFIDENCE_LEVELS else "medium",
        confidence_explanation=optional_text(confidence_explanation),
        contribution_level=contribution_level if contribution_level in CONTRIBUTION_LEVELS else "indeterminate",
        contribution_explanation=optional_text(contribution_explanation),
        contribution_confidence=contribution_confidence if contribution_confidence in CONFIDENCE_LEVELS else None,
        importance_level=importance_level if importance_level in IMPORTANCE_LEVELS else "standard",
        importance_weight=IMPORTANCE_LEVELS[importance_level if importance_level in IMPORTANCE_LEVELS else "standard"]["weight"],
        last_status_update=parse_date(last_status_update),
        is_key_commitment=bool(is_key_commitment),
        display_order=display_order,
        is_published=bool(is_published),
    )
    db.add(commitment)
    db.flush()
    if commitment.current_status != "not_analyzed":
        db.add(
            CommitmentStatusUpdate(
                commitment_id=commitment.id,
                previous_status="not_analyzed",
                new_status=commitment.current_status,
                previous_status_group="pending",
                new_status_group=commitment.status_group,
                previous_contribution_level="indeterminate",
                new_contribution_level=commitment.contribution_level,
                effective_date=commitment.last_status_update or date.today(),
                status_explanation=commitment.status_explanation,
                confidence=commitment.confidence,
                confidence_explanation=commitment.confidence_explanation,
                contribution_explanation=commitment.contribution_explanation,
                contribution_confidence=commitment.contribution_confidence,
                source_origin="manual",
                structural_status="parsed",
                factual_review_status="not_reviewed",
                changed_by_user_id=user.get("moderator").id if user.get("moderator") else None,
            )
        )
    create_entity_revision(db, commitment, user, "commitment_created")
    db.commit()
    write_audit_log(db, request, user, "create_commitment", "commitment", str(commitment.id), {"slug": commitment.slug})
    return RedirectResponse(f"/internal/programs/commitments/{commitment.id}/edit", status_code=303)


@router.get("/commitments/{commitment_id}/edit")
def edit_commitment(commitment_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    context = {
        "user": user,
        "commitment": get_commitment(db, commitment_id),
        "form_action": f"/internal/programs/commitments/{commitment_id}/edit",
        "form_title": "Edit commitment",
        "evidence": None,
    }
    context.update(form_options(db))
    return render(request, "internal/commitment_form.html", context)


@router.post("/commitments/{commitment_id}/edit")
def update_commitment(
    commitment_id: UUID,
    request: Request,
    program_id: str = Form(...),
    program_section_id: str = Form(""),
    title: str = Form(...),
    slug: str = Form(""),
    original_text: str = Form(...),
    normalized_description: str = Form(""),
    political_subject_name: str = Form(""),
    related_party_id: str = Form(""),
    related_coalition_name: str = Form(""),
    topic: str = Form(""),
    responsible_institutions: str = Form(""),
    period: str = Form(""),
    deadline: str = Form(""),
    measurable_criteria: str = Form(""),
    commitment_type: str = Form(""),
    promised_item_type: str = Form(""),
    baseline_mode: str = Form(""),
    required_external_actors: str = Form(""),
    control_level: str = Form(""),
    evaluation_basis: str = Form(""),
    contribution_types: str = Form(""),
    official_program_change_note: str = Form(""),
    source_version_note: str = Form(""),
    quantitative_target: str = Form(""),
    quantitative_actual: str = Form(""),
    measure_validity_status: str = Form(""),
    status: str = Form("not_started"),
    status_explanation: str = Form(""),
    confidence_level: str = Form("medium"),
    confidence_explanation: str = Form(""),
    contribution_level: str = Form("indeterminate"),
    contribution_explanation: str = Form(""),
    contribution_confidence: str = Form(""),
    importance_level: str = Form("standard"),
    importance_weight: int = Form(2),
    last_status_update: str = Form(""),
    is_key_commitment: str | None = Form(None),
    display_order: int = Form(0),
    is_published: str | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    commitment = get_commitment(db, commitment_id)
    previous_status = commitment.current_status
    previous_group = commitment.status_group
    previous_contribution = commitment.contribution_level
    if program_section_id:
        selected_section = db.get(ProgramSection, program_section_id)
        if not selected_section or str(selected_section.program_id) != program_id:
            raise HTTPException(status_code=400, detail="Selected section belongs to another program")
    commitment.program_id = program_id
    commitment.program_section_id = program_section_id or None
    commitment.title = title.strip()
    commitment.slug = ensure_unique_slug(db, Commitment, slug or title, commitment.id)
    commitment.original_text = original_text.strip()
    commitment.normalized_description = optional_text(normalized_description)
    commitment.political_subject_name = optional_text(political_subject_name)
    commitment.related_party_id = related_party_id or None
    commitment.related_coalition_name = optional_text(related_coalition_name)
    commitment.topic = optional_text(topic)
    commitment.responsible_institutions = optional_text(responsible_institutions)
    commitment.period = optional_text(period)
    commitment.deadline = parse_date(deadline)
    commitment.measurable_criteria = optional_text(measurable_criteria)
    commitment.commitment_type = commitment_type if commitment_type in COMMITMENT_TYPES else None
    commitment.promised_item_type = promised_item_type if promised_item_type in COMMITMENT_TYPES else None
    commitment.baseline_mode = baseline_mode if baseline_mode in BASELINE_MODES else None
    commitment.required_external_actors = optional_text(required_external_actors)
    commitment.control_level = control_level if control_level in CONTROL_LEVELS else None
    commitment.evaluation_basis = optional_text(evaluation_basis)
    commitment.contribution_types_text = optional_text(contribution_types)
    commitment.official_program_change_note = optional_text(official_program_change_note)
    commitment.source_version_note = optional_text(source_version_note)
    commitment.quantitative_target = optional_text(quantitative_target)
    commitment.quantitative_actual = optional_text(quantitative_actual)
    commitment.measure_validity_status = measure_validity_status if measure_validity_status in MEASURE_VALIDITY_STATUSES else None
    commitment.status = status if status in COMMITMENT_STATUSES else "not_started"
    commitment.status_group = status_group(commitment.status)
    commitment.status_explanation = optional_text(status_explanation)
    commitment.confidence_level = confidence_level if confidence_level in CONFIDENCE_LEVELS else "medium"
    commitment.confidence_explanation = optional_text(confidence_explanation)
    commitment.contribution_level = contribution_level if contribution_level in CONTRIBUTION_LEVELS else "indeterminate"
    commitment.contribution_explanation = optional_text(contribution_explanation)
    commitment.contribution_confidence = contribution_confidence if contribution_confidence in CONFIDENCE_LEVELS else None
    commitment.importance_level = importance_level if importance_level in IMPORTANCE_LEVELS else "standard"
    commitment.importance_weight = IMPORTANCE_LEVELS[commitment.importance_level]["weight"]
    commitment.last_status_update = parse_date(last_status_update)
    commitment.is_key_commitment = bool(is_key_commitment)
    commitment.display_order = display_order
    commitment.is_published = bool(is_published)
    if commitment.current_status != previous_status or commitment.contribution_level != previous_contribution:
        db.add(
            CommitmentStatusUpdate(
                commitment_id=commitment.id,
                previous_status=previous_status,
                new_status=commitment.current_status,
                previous_status_group=previous_group,
                new_status_group=commitment.status_group,
                previous_contribution_level=previous_contribution,
                new_contribution_level=commitment.contribution_level,
                effective_date=commitment.last_status_update or date.today(),
                status_explanation=commitment.status_explanation,
                confidence=commitment.confidence,
                confidence_explanation=commitment.confidence_explanation,
                contribution_explanation=commitment.contribution_explanation,
                contribution_confidence=commitment.contribution_confidence,
                source_origin="manual",
                structural_status="parsed",
                factual_review_status="not_reviewed",
                changed_by_user_id=user.get("moderator").id if user.get("moderator") else None,
            )
        )
    create_entity_revision(db, commitment, user, "commitment_updated")
    db.commit()
    write_audit_log(db, request, user, "update_commitment", "commitment", str(commitment.id), {"slug": commitment.slug})
    return RedirectResponse(f"/internal/programs/commitments/{commitment.id}/edit", status_code=303)


@router.post("/commitments/{commitment_id}/delete")
def delete_commitment(
    commitment_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    commitment = get_commitment(db, commitment_id)
    if commitment.program.is_published:
        raise HTTPException(status_code=409, detail="Unpublish the program before deleting a commitment")
    program_id = commitment.program_id
    title = commitment.title
    create_entity_revision(db, commitment, user, "commitment_deleted")
    db.delete(commitment)
    db.commit()
    write_audit_log(db, request, user, "delete_commitment", "commitment", str(commitment_id), {"title": title})
    return RedirectResponse(f"/internal/programs/{program_id}/preview", status_code=303)


@router.get("/commitments/{commitment_id}/status-prompt")
def commitment_status_prompt(
    commitment_id: UUID,
    request: Request,
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    try:
        result = workflow_generate_commitment_status_prompt(db, commitment_id, user)
    except ProgramWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    commitment = get_commitment(db, commitment_id)
    write_audit_log(
        db,
        request,
        user,
        "generate_commitment_status_prompt",
        "commitment",
        str(commitment.id),
        {"ai_run_id": str(result.ai_run.id)},
    )
    return render(
        request,
        "internal/program_prompt.html",
        {
            "user": user,
            "program": commitment.program,
            "ai_run": result.ai_run,
            "prompt": result.prompt,
            "heading": commitment.title,
            "prompt_title": "Commitment status analysis prompt",
            "prompt_note": "Copy this prompt into an external AI model. It analyzes only this commitment and must return evidence-backed JSON.",
            "form_action": f"/internal/programs/commitments/{commitment.id}/status-prompt",
        },
    )


@router.post("/commitments/{commitment_id}/status-prompt")
def save_commitment_status_prompt(
    commitment_id: UUID,
    request: Request,
    prompt_text: str = Form(...),
    ai_run_id: UUID | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    commitment = get_commitment(db, commitment_id)
    ai_run = save_prompt_run(
        db,
        ai_run_id,
        "commitment",
        commitment.id,
        COMMITMENT_STATUS_TASK,
        prompt_text,
        user,
        ai_run_context(commitment, COMMITMENT_STATUS_TASK),
    )
    db.commit()
    write_audit_log(db, request, user, "save_commitment_status_prompt", "commitment", str(commitment.id), {"ai_run_id": str(ai_run.id)})
    return RedirectResponse(f"/internal/programs/commitments/{commitment.id}/status-json?ai_run_id={ai_run.id}", status_code=303)


@router.get("/commitments/{commitment_id}/status-json")
def commitment_status_json_form(
    commitment_id: UUID,
    request: Request,
    ai_run_id: UUID | None = Query(default=None),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    commitment = get_commitment(db, commitment_id)
    ai_run = get_ai_run(db, ai_run_id, "commitment", commitment.id, COMMITMENT_STATUS_TASK)
    return render_ai_json(
        request,
        user,
        commitment.program,
        ai_run,
        ai_run.raw_ai_response if ai_run else "",
        heading=commitment.title,
        json_title="Import commitment status JSON",
        json_note="This updates the commitment current status, creates a status history row, and links AI-imported evidence. Factual review remains not reviewed.",
        form_action=f"/internal/programs/commitments/{commitment.id}/status-json",
    )


@router.post("/commitments/{commitment_id}/status-json")
async def save_commitment_status_json(
    commitment_id: UUID,
    request: Request,
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    raw_json, ai_run_id, _ = await parse_ai_json_form(request)
    try:
        result = workflow_import_commitment_status_json(db, commitment_id, raw_json, ai_run_id, user)
    except ProgramWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    commitment = result.commitment or get_commitment(db, commitment_id)
    if not result.ok:
        write_audit_log(
            db,
            request,
            user,
            "commitment_status_import_failed",
            "commitment",
            str(commitment.id),
            {"error": result.error},
        )
        return render_ai_json(
            request,
            user,
            commitment.program,
            result.ai_run,
            raw_json,
            error=result.error,
            heading=commitment.title,
            json_title="Import commitment status JSON",
            form_action=f"/internal/programs/commitments/{commitment.id}/status-json",
            status_code=result.status_code,
        )
    write_audit_log(
        db,
        request,
        user,
        "import_commitment_status",
        "commitment",
        str(commitment.id),
        {"ai_run_id": str(result.ai_run.id)},
    )
    return RedirectResponse(f"/internal/programs/commitments/{commitment.id}/edit", status_code=303)


@router.post("/commitments/{commitment_id}/evidence")
def create_evidence(
    commitment_id: UUID,
    request: Request,
    title: str = Form(...),
    url: str = Form(""),
    source_type: str = Form("other"),
    publisher: str = Form(""),
    published_at: str = Form(""),
    quote_or_relevant_excerpt: str = Form(""),
    description: str = Form(""),
    relation_type: str = Form("supports_status"),
    evidence_role: str = Form(""),
    evidence_strength: str = Form(""),
    is_self_reported: str | None = Form(None),
    is_independent_confirmation: str | None = Form(None),
    is_contradictory: str | None = Form(None),
    is_disproven: str | None = Form(None),
    limitations: str = Form(""),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    commitment = get_commitment(db, commitment_id)
    evidence_item = EvidenceItem(
        title=title.strip(),
        url=optional_text(url) or "",
        source_type=source_type if source_type in EVIDENCE_SOURCE_TYPES else "other",
        publisher=optional_text(publisher),
        published_at=parse_date(published_at),
        quote_or_relevant_excerpt=optional_text(quote_or_relevant_excerpt),
        description=optional_text(description),
        reliability_level="medium",
        source_origin="manual",
        structural_status="valid",
        factual_review_status="not_reviewed",
    )
    db.add(evidence_item)
    db.flush()
    evidence = CommitmentEvidence(
        commitment_id=commitment.id,
        evidence_item_id=evidence_item.id,
        relation_type=relation_type if relation_type in COMMITMENT_EVIDENCE_RELATION_TYPES else "background",
        evidence_role=evidence_role if evidence_role in EVIDENCE_ROLES else None,
        evidence_strength=evidence_strength if evidence_strength in EVIDENCE_STRENGTHS else None,
        is_self_reported=bool(is_self_reported),
        is_independent_confirmation=bool(is_independent_confirmation),
        is_contradictory=bool(is_contradictory),
        is_disproven=bool(is_disproven),
        limitations=optional_text(limitations),
        source_origin="manual",
    )
    db.add(evidence)
    create_entity_revision(db, evidence_item, user, "commitment_evidence_created")
    db.commit()
    write_audit_log(db, request, user, "create_commitment_evidence", "commitment", str(commitment.id), {"title": evidence.title})
    return RedirectResponse(f"/internal/programs/commitments/{commitment.id}/edit", status_code=303)


@router.get("/commitments/{commitment_id}/evidence/{evidence_id}/edit")
def edit_evidence(
    commitment_id: UUID,
    evidence_id: UUID,
    request: Request,
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    commitment = get_commitment(db, commitment_id)
    evidence = db.get(CommitmentEvidence, evidence_id)
    if not evidence or evidence.commitment_id != commitment.id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    context = {"user": user, "commitment": commitment, "evidence": evidence}
    context.update(form_options(db))
    return render(request, "internal/evidence_form.html", context)


@router.post("/commitments/{commitment_id}/evidence/{evidence_id}/edit")
def update_evidence(
    commitment_id: UUID,
    evidence_id: UUID,
    request: Request,
    title: str = Form(...),
    url: str = Form(""),
    source_type: str = Form("other"),
    publisher: str = Form(""),
    published_at: str = Form(""),
    quote_or_relevant_excerpt: str = Form(""),
    description: str = Form(""),
    relation_type: str = Form("supports_status"),
    evidence_role: str = Form(""),
    evidence_strength: str = Form(""),
    is_self_reported: str | None = Form(None),
    is_independent_confirmation: str | None = Form(None),
    is_contradictory: str | None = Form(None),
    is_disproven: str | None = Form(None),
    limitations: str = Form(""),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    evidence = db.get(CommitmentEvidence, evidence_id)
    if not evidence or evidence.commitment_id != commitment_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    evidence_item = evidence.evidence_item
    evidence_item.title = title.strip()
    evidence_item.url = optional_text(url) or ""
    evidence_item.source_type = source_type if source_type in EVIDENCE_SOURCE_TYPES else "other"
    evidence_item.publisher = optional_text(publisher)
    evidence_item.published_at = parse_date(published_at)
    evidence_item.quote_or_relevant_excerpt = optional_text(quote_or_relevant_excerpt)
    evidence_item.description = optional_text(description)
    evidence.relation_type = relation_type if relation_type in COMMITMENT_EVIDENCE_RELATION_TYPES else "background"
    evidence.evidence_role = evidence_role if evidence_role in EVIDENCE_ROLES else None
    evidence.evidence_strength = evidence_strength if evidence_strength in EVIDENCE_STRENGTHS else None
    evidence.is_self_reported = bool(is_self_reported)
    evidence.is_independent_confirmation = bool(is_independent_confirmation)
    evidence.is_contradictory = bool(is_contradictory)
    evidence.is_disproven = bool(is_disproven)
    evidence.limitations = optional_text(limitations)
    create_entity_revision(db, evidence_item, user, "commitment_evidence_updated")
    db.commit()
    write_audit_log(db, request, user, "update_commitment_evidence", "commitment", str(commitment_id), {"title": evidence.title})
    return RedirectResponse(f"/internal/programs/commitments/{commitment_id}/edit", status_code=303)


@router.post("/commitments/{commitment_id}/evidence/{evidence_id}/delete")
def delete_evidence(
    commitment_id: UUID,
    evidence_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    evidence = db.get(CommitmentEvidence, evidence_id)
    if evidence and evidence.commitment_id == commitment_id:
        db.delete(evidence)
        db.commit()
        write_audit_log(db, request, user, "delete_commitment_evidence", "commitment", str(commitment_id))
    return RedirectResponse(f"/internal/programs/commitments/{commitment_id}/edit", status_code=303)


