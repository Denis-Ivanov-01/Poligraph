from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.responses import RedirectResponse

from app.database import get_db
from app.dependencies import current_internal_user, root_admin_required
from app.models.commitment import Commitment, CommitmentEvidence
from app.models.political_party import PoliticalParty
from app.models.program import Program
from app.routers.internal.utils import render
from app.security import validate_csrf
from app.services.audit_service import write_audit_log
from app.services.commitment_service import (
    COMMITMENT_STATUSES,
    CONFIDENCE_LEVELS,
    EVIDENCE_SOURCE_TYPES,
    PROGRAM_TYPES,
    build_commitment_extraction_prompt,
    ensure_unique_slug,
    optional_text,
    parse_date,
    status_group,
    unset_other_active_programs,
    validate_import_json,
)

router = APIRouter(prefix="/internal/programs", tags=["internal-programs"])


def program_query():
    return select(Program).where(Program.is_deleted.is_(False)).options(selectinload(Program.related_party)).order_by(
        Program.is_active_government_program.desc(),
        Program.created_at.desc(),
    )


def commitment_query():
    return (
        select(Commitment)
        .options(selectinload(Commitment.program), selectinload(Commitment.related_party), selectinload(Commitment.evidence))
        .order_by(Commitment.display_order, Commitment.created_at.desc())
    )


def form_options(db: Session) -> dict:
    return {
        "parties": db.scalars(select(PoliticalParty).where(PoliticalParty.is_deleted.is_(False)).order_by(PoliticalParty.full_name)).all(),
        "programs": db.scalars(select(Program).where(Program.is_deleted.is_(False)).order_by(Program.title)).all(),
        "program_types": PROGRAM_TYPES,
        "statuses": COMMITMENT_STATUSES,
        "confidence_levels": CONFIDENCE_LEVELS,
        "evidence_source_types": EVIDENCE_SOURCE_TYPES,
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


def apply_program_ai_import(db: Session, program: Program, data: dict, raw_json: str) -> int:
    program.raw_ai_response = raw_json
    program_data = data["program"]
    program.description = program.description or optional_text(program_data.get("description"))
    program.source_title = program.source_title or optional_text(program_data.get("source_title"))
    program.related_coalition_name = program.related_coalition_name or optional_text(program_data.get("related_coalition_name"))
    program.period_start = program.period_start or parse_date(program_data.get("period_start"))
    program.period_end = program.period_end or parse_date(program_data.get("period_end"))

    existing_commitments = db.scalars(
        select(Commitment).options(selectinload(Commitment.evidence)).where(Commitment.program_id == program.id)
    ).all()
    for existing_commitment in existing_commitments:
        db.delete(existing_commitment)
    db.flush()

    for index, item in enumerate(data["commitments"]):
        initial_status = item.get("initial_status", "not_started")
        commitment = Commitment(
            program_id=program.id,
            title=item["title"].strip(),
            slug=ensure_unique_slug(db, Commitment, item["title"]),
            original_text=item["original_text"].strip(),
            normalized_description=optional_text(item.get("normalized_description")),
            political_subject_name=program.political_subject_name,
            related_party_id=program.related_party_id,
            related_coalition_name=program.related_coalition_name,
            topic=optional_text(item.get("topic")),
            responsible_institutions=", ".join(item.get("responsible_institutions") or []) or None,
            period=optional_text(item.get("period")),
            deadline=parse_date(item.get("deadline")),
            measurable_criteria=optional_text(item.get("measurable_criteria")),
            status=initial_status,
            status_group=status_group(initial_status),
            confidence_level=item.get("confidence_level", "medium"),
            confidence_explanation=optional_text(item.get("confidence_explanation")),
            display_order=index,
            is_key_commitment=index < 5,
            is_published=False,
        )
        db.add(commitment)
        db.flush()
        for note_index, note in enumerate(item.get("source_notes") or [], start=1):
            if not optional_text(str(note)):
                continue
            db.add(
                CommitmentEvidence(
                    commitment_id=commitment.id,
                    title=f"Source note {note_index}",
                    source_type="other",
                    description=str(note),
                    supports_status=False,
                )
            )
    return len(data["commitments"])


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
    period_start: str = Form(""),
    period_end: str = Form(""),
    source_url: str = Form(""),
    source_title: str = Form(""),
    source_description: str = Form(""),
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
        period_start=parse_date(period_start),
        period_end=parse_date(period_end),
        source_url=optional_text(source_url),
        source_title=optional_text(source_title),
        source_description=optional_text(source_description),
        is_active_government_program=active,
        is_published=False,
    )
    if active:
        unset_other_active_programs(db)
    db.add(program)
    db.commit()
    write_audit_log(db, request, user, "create_program", "program", str(program.id), {"slug": program.slug})
    return RedirectResponse(f"/internal/programs/{program.id}/prompt", status_code=303)


@router.get("/{program_id}/prompt")
def program_prompt(program_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    program = get_program(db, program_id)
    period = " - ".join(str(item) for item in (program.period_start, program.period_end) if item)
    if not program.generated_prompt_text:
        program.generated_prompt_text = build_commitment_extraction_prompt(
            program.source_url,
            program.source_description,
            program.political_subject_name,
            program.program_type,
            period or None,
            program.description,
        )
        db.commit()
    prompt = program.generated_prompt_text
    return render(request, "internal/program_prompt.html", {"user": user, "program": program, "prompt": prompt})


@router.post("/{program_id}/prompt")
def save_program_prompt(
    program_id: UUID,
    request: Request,
    prompt_text: str = Form(...),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    program = get_program(db, program_id)
    program.generated_prompt_text = prompt_text
    db.commit()
    write_audit_log(db, request, user, "save_program_ai_prompt", "program", str(program.id))
    return RedirectResponse(f"/internal/programs/{program.id}/ai-json", status_code=303)


@router.get("/{program_id}/ai-json")
def program_ai_json_form(program_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    program = get_program(db, program_id)
    return render(request, "internal/program_ai_json.html", {"user": user, "program": program, "raw_json": program.raw_ai_response or ""})


@router.post("/{program_id}/ai-json")
def save_program_ai_json(
    program_id: UUID,
    request: Request,
    raw_json: str = Form(...),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    program = get_program(db, program_id)
    try:
        data = validate_import_json(raw_json)
    except ValueError as exc:
        return render(
            request,
            "internal/program_ai_json.html",
            {"user": user, "program": program, "error": str(exc), "raw_json": raw_json},
            status_code=400,
        )

    commitment_count = apply_program_ai_import(db, program, data, raw_json)
    db.commit()
    write_audit_log(db, request, user, "save_program_ai_json", "program", str(program.id), {"commitment_count": commitment_count})
    return RedirectResponse(f"/internal/programs/{program.id}/preview", status_code=303)


@router.get("/{program_id}/preview")
def program_preview(program_id: UUID, request: Request, user: dict = Depends(current_internal_user), db: Session = Depends(get_db)):
    program = get_program(db, program_id)
    commitments = db.scalars(commitment_query().where(Commitment.program_id == program.id)).all()
    return render(
        request,
        "internal/program_preview.html",
        {"user": user, "program": program, "commitments": commitments, "statuses": COMMITMENT_STATUSES, "confidence_levels": CONFIDENCE_LEVELS},
    )


@router.post("/{program_id}/publish")
def publish_program(
    program_id: UUID,
    request: Request,
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    program = get_program(db, program_id)
    if program.is_active_government_program:
        unset_other_active_programs(db, program)
    program.is_published = True
    commitments = db.scalars(select(Commitment).where(Commitment.program_id == program.id)).all()
    for commitment in commitments:
        commitment.is_published = True
    db.commit()
    write_audit_log(db, request, user, "publish_program", "program", str(program.id), {"commitment_count": len(commitments)})
    return RedirectResponse("/internal/programs", status_code=303)


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
    source_url: str = Form(""),
    source_title: str = Form(""),
    source_description: str = Form(""),
    generated_prompt_text: str = Form(""),
    raw_ai_response: str = Form(""),
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
    program.period_start = parse_date(period_start)
    program.period_end = parse_date(period_end)
    program.source_url = optional_text(source_url)
    program.source_title = optional_text(source_title)
    program.source_description = optional_text(source_description)
    program.generated_prompt_text = optional_text(generated_prompt_text)
    program.is_active_government_program = active
    program.is_published = bool(is_published)
    if raw_ai_response.strip() and raw_ai_response != (program.raw_ai_response or ""):
        try:
            data = validate_import_json(raw_ai_response)
        except ValueError as exc:
            context = {
                "user": user,
                "program": program,
                "form_action": f"/internal/programs/{program_id}/edit",
                "form_title": "Edit program",
                "form_note": "Update program details. Publishing happens from the preview step.",
                "submit_label": "Save changes",
                "show_publish_controls": True,
                "error": str(exc),
            }
            context.update(form_options(db))
            return render(request, "internal/program_form.html", context, status_code=400)
        apply_program_ai_import(db, program, data, raw_ai_response)
    elif not raw_ai_response.strip():
        program.raw_ai_response = None
    if program.is_published:
        commitments = db.scalars(select(Commitment).where(Commitment.program_id == program.id)).all()
        for commitment in commitments:
            commitment.is_published = True
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
        query = query.where(Commitment.status == status)
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
    status: str = Form("not_started"),
    status_explanation: str = Form(""),
    confidence_level: str = Form("medium"),
    confidence_explanation: str = Form(""),
    last_status_update: str = Form(""),
    is_key_commitment: str | None = Form(None),
    display_order: int = Form(0),
    is_published: str | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    commitment = Commitment(
        program_id=program_id,
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
        status=status if status in COMMITMENT_STATUSES else "not_started",
        status_group=status_group(status),
        status_explanation=optional_text(status_explanation),
        confidence_level=confidence_level if confidence_level in CONFIDENCE_LEVELS else "medium",
        confidence_explanation=optional_text(confidence_explanation),
        last_status_update=parse_date(last_status_update),
        is_key_commitment=bool(is_key_commitment),
        display_order=display_order,
        is_published=bool(is_published),
    )
    db.add(commitment)
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
    status: str = Form("not_started"),
    status_explanation: str = Form(""),
    confidence_level: str = Form("medium"),
    confidence_explanation: str = Form(""),
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
    commitment.program_id = program_id
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
    commitment.status = status if status in COMMITMENT_STATUSES else "not_started"
    commitment.status_group = status_group(commitment.status)
    commitment.status_explanation = optional_text(status_explanation)
    commitment.confidence_level = confidence_level if confidence_level in CONFIDENCE_LEVELS else "medium"
    commitment.confidence_explanation = optional_text(confidence_explanation)
    commitment.last_status_update = parse_date(last_status_update)
    commitment.is_key_commitment = bool(is_key_commitment)
    commitment.display_order = display_order
    commitment.is_published = bool(is_published)
    db.commit()
    write_audit_log(db, request, user, "update_commitment", "commitment", str(commitment.id), {"slug": commitment.slug})
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
    supports_status: str | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    commitment = get_commitment(db, commitment_id)
    evidence = CommitmentEvidence(
        commitment_id=commitment.id,
        title=title.strip(),
        url=optional_text(url),
        source_type=source_type if source_type in EVIDENCE_SOURCE_TYPES else "other",
        publisher=optional_text(publisher),
        published_at=parse_date(published_at),
        quote_or_relevant_excerpt=optional_text(quote_or_relevant_excerpt),
        description=optional_text(description),
        supports_status=bool(supports_status),
    )
    db.add(evidence)
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
    supports_status: str | None = Form(None),
    csrf_token: str = Form(...),
    user: dict = Depends(current_internal_user),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    evidence = db.get(CommitmentEvidence, evidence_id)
    if not evidence or evidence.commitment_id != commitment_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    evidence.title = title.strip()
    evidence.url = optional_text(url)
    evidence.source_type = source_type if source_type in EVIDENCE_SOURCE_TYPES else "other"
    evidence.publisher = optional_text(publisher)
    evidence.published_at = parse_date(published_at)
    evidence.quote_or_relevant_excerpt = optional_text(quote_or_relevant_excerpt)
    evidence.description = optional_text(description)
    evidence.supports_status = bool(supports_status)
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


