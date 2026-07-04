from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.party_membership import PartyMembership
from app.models.political_party import PoliticalParty
from app.models.statement import Statement
from app.routers.public.utils import average_scores_payload, statement_list_payload
from app.schemas.political_party import PoliticalPartyPublic

router = APIRouter(prefix="/parties", tags=["public-parties"])


@router.get("", response_model=list[PoliticalPartyPublic])
def list_parties(db: Session = Depends(get_db)):
    return db.scalars(select(PoliticalParty).where(PoliticalParty.is_deleted.is_(False)).order_by(PoliticalParty.full_name)).all()


@router.get("/{slug}")
def party_by_slug(slug: str, db: Session = Depends(get_db)):
    party = db.scalar(
        select(PoliticalParty)
        .where(PoliticalParty.slug == slug, PoliticalParty.is_deleted.is_(False))
        .options(selectinload(PoliticalParty.memberships).selectinload(PartyMembership.politician))
    )
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    statements = db.scalars(
        select(Statement)
        .where(
            Statement.party_at_statement_time_id == party.id,
            Statement.status == "published",
            Statement.is_deleted.is_(False),
            Statement.is_archived.is_(False),
        )
        .options(selectinload(Statement.politician), selectinload(Statement.party_at_statement_time), selectinload(Statement.ai_analysis))
        .order_by(Statement.statement_date.desc().nullslast(), Statement.published_at.desc().nullslast(), Statement.created_at.desc())
    ).all()
    return {
        "id": party.id,
        "slug": party.slug,
        "full_name": party.full_name,
        "short_name": party.short_name,
        "description": party.description,
        "average_scores": average_scores_payload(statements),
        "members": [
            {
                "id": membership.id,
                "start_date": membership.start_date,
                "end_date": membership.end_date,
                "politician": {
                    "id": membership.politician.id,
                    "slug": membership.politician.slug,
                    "full_name": membership.politician.full_name,
                    "biography": membership.politician.biography,
                    "image_url": membership.politician.image_url,
                    "current_party": {
                        "id": party.id,
                        "slug": party.slug,
                        "full_name": party.full_name,
                        "short_name": party.short_name,
                        "description": party.description,
                    }
                    if membership.end_date is None
                    else None,
                },
            }
            for membership in sorted(
                party.memberships,
                key=lambda item: (item.end_date is not None, item.politician.full_name),
            )
            if not membership.politician.is_deleted
        ],
        "statements": [statement_list_payload(statement) for statement in statements],
    }
