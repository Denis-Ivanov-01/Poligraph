from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.commitment import Commitment
from app.models.program import Program
from app.services.commitment_service import (
    active_government_program_summary,
    commitment_payload,
    commitment_query,
    program_payload,
    program_status_counts,
    topic_options,
)

router = APIRouter(prefix="/programs", tags=["public-programs"])


@router.get("")
def list_programs(db: Session = Depends(get_db)):
    programs = db.scalars(
        select(Program)
        .where(Program.is_published.is_(True), Program.is_deleted.is_(False))
        .options(selectinload(Program.related_party))
        .order_by(Program.is_active_government_program.desc(), Program.created_at.desc())
    ).all()
    return [program_payload(program) for program in programs]


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
        query = query.where(Commitment.status == status)
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


@router.get("/{program_id}/status-counts")
def status_counts(program_id: UUID, db: Session = Depends(get_db)):
    program = db.scalar(select(Program).where(Program.id == program_id, Program.is_published.is_(True), Program.is_deleted.is_(False)))
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program_status_counts(db, program.id)
