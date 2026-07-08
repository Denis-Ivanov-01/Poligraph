import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    program_type: Mapped[str] = mapped_column(String(80), default="other", index=True)
    political_subject_name: Mapped[str] = mapped_column(String(255))
    related_party_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("political_parties.id"))
    related_coalition_name: Mapped[str | None] = mapped_column(String(255))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_title: Mapped[str | None] = mapped_column(String(255))
    source_description: Mapped[str | None] = mapped_column(Text)
    generated_prompt_text: Mapped[str | None] = mapped_column(Text)
    raw_ai_response: Mapped[str | None] = mapped_column(Text)
    is_active_government_program: Mapped[bool] = mapped_column(default=False, index=True)
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    related_party = relationship("PoliticalParty", back_populates="programs")
    commitments = relationship("Commitment", back_populates="program", cascade="all, delete-orphan")
