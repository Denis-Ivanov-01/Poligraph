from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.commitment import Commitment
from app.models.program import Program, ProgramSection
from app.services.commitment_service import (
    active_government_program_summary,
    commitment_payload,
    commitment_query,
    commitment_rows_page,
    program_last_commitment_update,
    program_payload,
    program_score_summary,
    program_section_summaries,
    program_status_counts,
    topic_options,
)

router = APIRouter(prefix="/programs", tags=["public-programs"])


def public_program_or_404(db: Session, program_id: UUID) -> Program:
    program = db.scalar(
        select(Program)
        .where(Program.id == program_id, Program.is_published.is_(True), Program.is_deleted.is_(False))
        .options(selectinload(Program.related_party))
    )
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


def public_section_or_404(db: Session, program_id: UUID, section_id: UUID) -> ProgramSection:
    section = db.scalar(
        select(ProgramSection)
        .join(Program)
        .where(
            ProgramSection.id == section_id,
            ProgramSection.program_id == program_id,
            Program.id == program_id,
            Program.is_published.is_(True),
            Program.is_deleted.is_(False),
        )
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


@router.get("")
def list_programs(db: Session = Depends(get_db)):
    programs = db.scalars(
        select(Program)
        .where(Program.is_published.is_(True), Program.is_deleted.is_(False))
        .options(selectinload(Program.related_party))
        .order_by(Program.is_active_government_program.desc(), Program.created_at.desc())
    ).all()
    items = []
    for program in programs:
        payload = program_payload(program)
        counts = program_status_counts(db, program.id)
        commitments = db.scalars(commitment_query().where(Commitment.program_id == program.id, Commitment.is_published.is_(True))).all()
        payload["status_counts"] = counts
        payload["total_commitments"] = sum(counts.values())
        payload["score_summary"] = program_score_summary(commitments)
        items.append(payload)
    return items


@router.get("/active-summary")
def active_summary(db: Session = Depends(get_db)):
    return active_government_program_summary(db)


@router.get("/commitments")
def list_commitments(
    status: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    key_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    query = commitment_query().join(Program).where(
        Commitment.is_published.is_(True),
        Program.is_published.is_(True),
        Program.is_deleted.is_(False),
    )
    if status:
        if status == "not_analyzed":
            query = query.where(~Commitment.status_updates.any())
        else:
            query = query.where(Commitment.current_status == status, Commitment.status_updates.any())
    if topic:
        query = query.where(Commitment.topic == topic)
    if program_id:
        query = query.where(Commitment.program_id == program_id)
    if key_only:
        query = query.where(Commitment.is_key_commitment.is_(True))
    commitments = db.scalars(query.order_by(Commitment.display_order, Commitment.created_at.desc())).all()
    return {
        "items": [commitment_payload(commitment) for commitment in commitments],
        "topics": topic_options(db),
    }


@router.get("/commitments/{slug}")
def commitment_by_slug(slug: str, db: Session = Depends(get_db)):
    commitment = db.scalar(
        commitment_query()
        .join(Program)
        .where(
            Commitment.slug == slug,
            Commitment.is_published.is_(True),
            Program.is_published.is_(True),
            Program.is_deleted.is_(False),
        )
    )
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return commitment_payload(commitment, include_evidence=True)


@router.get("/{program_id}/commitments")
def program_commitments(
    program_id: UUID,
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    confidence: str | None = Query(default=None),
    sort: str = Query(default="order"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    program = public_program_or_404(db, program_id)
    return commitment_rows_page(
        db,
        program,
        q=q,
        status=status,
        confidence=confidence,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/{program_id}/commitments/{slug}")
def commitment_by_program_and_slug(program_id: UUID, slug: str, db: Session = Depends(get_db)):
    commitment = db.scalar(
        commitment_query()
        .join(Program)
        .where(
            Commitment.program_id == program_id,
            Commitment.slug == slug,
            Commitment.is_published.is_(True),
            Program.id == program_id,
            Program.is_published.is_(True),
            Program.is_deleted.is_(False),
        )
    )
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return commitment_payload(commitment, include_evidence=True)


@router.get("/{program_id}/sections/{section_id}/subsections")
def section_subsections(program_id: UUID, section_id: UUID, db: Session = Depends(get_db)):
    public_section_or_404(db, program_id, section_id)
    return {"items": program_section_summaries(db, program_id, parent_section_id=section_id)}


@router.get("/{program_id}/sections/{section_id}/commitments")
def section_commitments(
    program_id: UUID,
    section_id: UUID,
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    confidence: str | None = Query(default=None),
    sort: str = Query(default="order"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    program = public_program_or_404(db, program_id)
    public_section_or_404(db, program_id, section_id)
    return commitment_rows_page(
        db,
        program,
        section_id=section_id,
        q=q,
        status=status,
        confidence=confidence,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/{program_id}/status-counts")
def status_counts(program_id: UUID, db: Session = Depends(get_db)):
    program = public_program_or_404(db, program_id)
    return program_status_counts(db, program.id)


@router.get("/{program_id}")
def program_by_id(program_id: UUID, db: Session = Depends(get_db)):
    program = public_program_or_404(db, program_id)
    counts = program_status_counts(db, program.id)
    payload = program_payload(program)
    payload["status_counts"] = counts
    payload["total_commitments"] = sum(counts.values())
    commitments = db.scalars(commitment_query().where(Commitment.program_id == program.id, Commitment.is_published.is_(True))).all()
    payload["score_summary"] = program_score_summary(commitments)
    payload["last_commitment_update"] = program_last_commitment_update(db, program.id)
    payload["sections"] = program_section_summaries(db, program.id)
    payload["disclaimer"] = (
        "Този анализ е генериран с помощта на AI според методологията на платформата и е преминал структурна "
        "модераторска проверка. Това не означава, че всеки източник е бил ръчно фактологично проверен. "
        "При открита грешка анализът може да бъде коригиран."
    )
    return payload
