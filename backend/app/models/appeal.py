import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Appeal(Base):
    __tablename__ = "appeals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    statement_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("statements.id"))
    program_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("programs.id"))
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("commitments.id"))
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"))
    submitter_name: Mapped[str | None] = mapped_column(String(255))
    submitter_email: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="new")
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
