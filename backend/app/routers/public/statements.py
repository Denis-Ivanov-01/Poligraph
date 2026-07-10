from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.statement import Statement
from app.routers.public.utils import statement_detail_payload, statement_list_payload

router = APIRouter(prefix="/statements", tags=["public-statements"])


def published_statement_query():
    return (
        select(Statement)
        .where(Statement.status == "published", Statement.is_deleted.is_(False), Statement.is_archived.is_(False))
        .options(
            selectinload(Statement.politician),
            selectinload(Statement.party_at_statement_time),
            selectinload(Statement.ai_analysis),
            selectinload(Statement.claims),
            selectinload(Statement.media),
        )
    )


@router.get("")
def list_statements(q: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = published_statement_query().order_by(Statement.published_at.desc().nullslast(), Statement.created_at.desc())
    if q:
        query = query.where(func.coalesce(Statement.title, "").ilike(f"%{q}%") | Statement.original_text.ilike(f"%{q}%"))
    return [statement_list_payload(item) for item in db.scalars(query).all()]


@router.get("/{statement_id}")
def statement_by_id(statement_id: UUID, db: Session = Depends(get_db)):
    statement = db.scalar(published_statement_query().where(Statement.id == statement_id))
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement_detail_payload(statement)
