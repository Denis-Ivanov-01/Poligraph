from uuid import UUID

from app.schemas.common import OrmModel


class PoliticalPartyPublic(OrmModel):
    id: UUID
    slug: str
    full_name: str
    short_name: str
    description: str | None = None
