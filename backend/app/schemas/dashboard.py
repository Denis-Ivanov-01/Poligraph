from pydantic import BaseModel

from app.schemas.statement import StatementListItem


class DashboardResponse(BaseModel):
    published_statement_count: int
    party_count: int
    politician_count: int
    average_overall_score: float | None
    latest_statements: list[StatementListItem]
