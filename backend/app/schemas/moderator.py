from uuid import UUID

from app.schemas.common import OrmModel


class ModeratorPublic(OrmModel):
    id: UUID
    username: str
    is_active: bool
