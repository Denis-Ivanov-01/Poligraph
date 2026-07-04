from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.ai_analysis import AiAnalysis
from app.models.political_party import PoliticalParty
from app.models.politician import Politician
from app.models.statement import Statement


def dashboard_data(db: Session) -> dict:
    published = (
        select(Statement)
        .where(Statement.status == "published", Statement.is_deleted.is_(False), Statement.is_archived.is_(False))
        .options(selectinload(Statement.politician), selectinload(Statement.party_at_statement_time), selectinload(Statement.ai_analysis))
        .order_by(Statement.published_at.desc().nullslast(), Statement.created_at.desc())
        .limit(10)
    )
    average = db.scalar(
        select(func.avg(AiAnalysis.overall_score)).join(Statement).where(
            Statement.status == "published",
            Statement.is_deleted.is_(False),
            Statement.is_archived.is_(False),
            AiAnalysis.is_published.is_(True),
        )
    )
    return {
        "published_statement_count": db.scalar(
            select(func.count()).select_from(Statement).where(
                Statement.status == "published",
                Statement.is_deleted.is_(False),
                Statement.is_archived.is_(False),
            )
        )
        or 0,
        "party_count": db.scalar(select(func.count()).select_from(PoliticalParty).where(PoliticalParty.is_deleted.is_(False))) or 0,
        "politician_count": db.scalar(select(func.count()).select_from(Politician).where(Politician.is_deleted.is_(False))) or 0,
        "average_overall_score": round(float(average), 2) if average is not None else None,
        "latest_statements": list(db.scalars(published)),
    }
