from uuid import UUID

from pydantic import BaseModel

from app.schemas.statement import StatementListItem


class DashboardRankingItem(BaseModel):
    id: UUID
    slug: str
    full_name: str
    short_name: str | None = None
    average_overall_score: float
    analyzed_statement_count: int


class DashboardResponse(BaseModel):
    published_statement_count: int
    party_count: int
    politician_count: int
    average_overall_score: float | None
    latest_statements: list[StatementListItem]
    top_politicians: list[DashboardRankingItem]
    top_parties: list[DashboardRankingItem]
