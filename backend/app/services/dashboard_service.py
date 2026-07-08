from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.ai_analysis import AiAnalysis
from app.models.political_party import PoliticalParty
from app.models.politician import Politician
from app.models.statement import Statement
from app.services.commitment_service import active_government_program_summary


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
    politician_average_score = func.avg(AiAnalysis.overall_score).label("average_overall_score")
    politician_statement_count = func.count(Statement.id).label("analyzed_statement_count")
    top_politicians = db.execute(
        select(
            Politician.id,
            Politician.slug,
            Politician.full_name,
            politician_average_score,
            politician_statement_count,
        )
        .join(Statement, Statement.politician_id == Politician.id)
        .join(AiAnalysis, AiAnalysis.statement_id == Statement.id)
        .where(
            Politician.is_deleted.is_(False),
            Statement.status == "published",
            Statement.is_deleted.is_(False),
            Statement.is_archived.is_(False),
            AiAnalysis.is_published.is_(True),
        )
        .group_by(Politician.id, Politician.slug, Politician.full_name)
        .order_by(politician_average_score.desc(), politician_statement_count.desc(), Politician.full_name)
        .limit(5)
    ).all()
    party_average_score = func.avg(AiAnalysis.overall_score).label("average_overall_score")
    party_statement_count = func.count(Statement.id).label("analyzed_statement_count")
    top_parties = db.execute(
        select(
            PoliticalParty.id,
            PoliticalParty.slug,
            PoliticalParty.full_name,
            PoliticalParty.short_name,
            party_average_score,
            party_statement_count,
        )
        .join(Statement, Statement.party_at_statement_time_id == PoliticalParty.id)
        .join(AiAnalysis, AiAnalysis.statement_id == Statement.id)
        .where(
            PoliticalParty.is_deleted.is_(False),
            Statement.status == "published",
            Statement.is_deleted.is_(False),
            Statement.is_archived.is_(False),
            AiAnalysis.is_published.is_(True),
        )
        .group_by(PoliticalParty.id, PoliticalParty.slug, PoliticalParty.full_name, PoliticalParty.short_name)
        .order_by(party_average_score.desc(), party_statement_count.desc(), PoliticalParty.full_name)
        .limit(5)
    ).all()
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
        "top_politicians": [
            {
                "id": item.id,
                "slug": item.slug,
                "full_name": item.full_name,
                "average_overall_score": round(float(item.average_overall_score), 2),
                "analyzed_statement_count": item.analyzed_statement_count,
            }
            for item in top_politicians
        ],
        "top_parties": [
            {
                "id": item.id,
                "slug": item.slug,
                "full_name": item.full_name,
                "short_name": item.short_name,
                "average_overall_score": round(float(item.average_overall_score), 2),
                "analyzed_statement_count": item.analyzed_statement_count,
            }
            for item in top_parties
        ],
        "active_government_program_summary": active_government_program_summary(db),
    }
