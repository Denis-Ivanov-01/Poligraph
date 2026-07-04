from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.ai_analysis import AiAnalysisPublic
from app.schemas.common import OrmModel
from app.schemas.political_party import PoliticalPartyPublic


class StatementPolitician(OrmModel):
    id: UUID
    slug: str
    full_name: str


class MediaAssetPublic(BaseModel):
    id: UUID
    file_path: str
    media_type: str
    original_filename: str | None = None


class StatementListItem(BaseModel):
    id: UUID
    title: str | None = None
    source_type: str
    statement_date: date | None = None
    politician: StatementPolitician
    party_at_statement_time: PoliticalPartyPublic | None = None
    overall_score: int | None = None


class StatementPublic(StatementListItem):
    source_url: str | None = None
    original_text: str
    media: list[MediaAssetPublic]
    ai_analysis: AiAnalysisPublic | None = None
