import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StatementCommitment(Base):
    __tablename__ = "statement_commitments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    statement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("statements.id"), index=True)
    commitment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("commitments.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(80), default="mentions")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
