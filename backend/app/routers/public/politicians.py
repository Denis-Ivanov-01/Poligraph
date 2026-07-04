from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.party_membership import PartyMembership
from app.models.politician import Politician
from app.models.statement import Statement
from app.routers.public.utils import average_scores_payload, statement_list_payload

router = APIRouter(prefix="/politicians", tags=["public-politicians"])


def politician_payload(politician: Politician) -> dict:
    current = next((membership.party for membership in politician.memberships if membership.end_date is None), None)
    return {
        "id": politician.id,
        "slug": politician.slug,
        "full_name": politician.full_name,
        "biography": politician.biography,
        "image_url": politician.image_url,
        "current_party": current,
    }


@router.get("")
def list_politicians(db: Session = Depends(get_db)):
    politicians = db.scalars(
        select(Politician)
        .where(Politician.is_deleted.is_(False))
        .options(selectinload(Politician.memberships).selectinload(PartyMembership.party))
        .order_by(Politician.full_name)
    ).all()
    return [politician_payload(item) for item in politicians]


@router.get("/{slug}")
def politician_by_slug(slug: str, db: Session = Depends(get_db)):
    politician = db.scalar(
        select(Politician)
        .where(Politician.slug == slug, Politician.is_deleted.is_(False))
        .options(selectinload(Politician.memberships).selectinload(PartyMembership.party))
    )
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    statements = db.scalars(
        select(Statement)
        .where(
            Statement.politician_id == politician.id,
            Statement.status == "published",
            Statement.is_deleted.is_(False),
            Statement.is_archived.is_(False),
        )
        .options(selectinload(Statement.politician), selectinload(Statement.party_at_statement_time), selectinload(Statement.ai_analysis))
        .order_by(Statement.statement_date.desc().nullslast(), Statement.published_at.desc().nullslast(), Statement.created_at.desc())
    ).all()
    payload = politician_payload(politician)
    payload.update(
        {
            "average_scores": average_scores_payload(statements),
            "statements": [statement_list_payload(statement) for statement in statements],
        }
    )
    return payload
