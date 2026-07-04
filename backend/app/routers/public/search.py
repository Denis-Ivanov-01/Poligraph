from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.party_membership import PartyMembership
from app.models.political_party import PoliticalParty
from app.models.politician import Politician
from app.models.statement import Statement
from app.routers.public.politicians import politician_payload
from app.routers.public.utils import statement_list_payload

router = APIRouter(prefix="/search", tags=["public-search"])


@router.get("")
def search(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    like = f"%{q}%"
    parties = db.scalars(
        select(PoliticalParty).where(PoliticalParty.is_deleted.is_(False), PoliticalParty.full_name.ilike(like)).limit(10)
    ).all()
    politicians = db.scalars(
        select(Politician)
        .where(Politician.is_deleted.is_(False), Politician.full_name.ilike(like))
        .options(selectinload(Politician.memberships).selectinload(PartyMembership.party))
        .limit(10)
    ).all()
    statements = db.scalars(
        select(Statement)
        .where(
            Statement.status == "published",
            Statement.is_deleted.is_(False),
            Statement.is_archived.is_(False),
            func.coalesce(Statement.title, "").ilike(like) | Statement.original_text.ilike(like),
        )
        .options(selectinload(Statement.politician), selectinload(Statement.party_at_statement_time), selectinload(Statement.ai_analysis))
        .limit(10)
    ).all()
    return {
        "parties": parties,
        "politicians": [politician_payload(item) for item in politicians],
        "statements": [statement_list_payload(item) for item in statements],
    }
