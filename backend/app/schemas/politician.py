from uuid import UUID

from app.schemas.common import OrmModel
from app.schemas.political_party import PoliticalPartyPublic


class PoliticianPublic(OrmModel):
    id: UUID
    slug: str
    full_name: str
    biography: str | None = None
    image_url: str | None = None
    current_party: PoliticalPartyPublic | None = None
