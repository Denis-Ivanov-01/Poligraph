import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EntityRevision(Base):
    __tablename__ = "entity_revisions"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "revision_number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(120), index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    data_json: Mapped[dict] = mapped_column(JSONB)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    change_note: Mapped[str | None] = mapped_column(Text)
