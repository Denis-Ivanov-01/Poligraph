import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(80))
    source_url: Mapped[str | None] = mapped_column(String(500))
    original_text: Mapped[str] = mapped_column(Text)
    statement_date: Mapped[date | None] = mapped_column(Date)
    politician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("politicians.id"))
    party_at_statement_time_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("political_parties.id"))
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(default=False)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    politician = relationship("Politician", back_populates="statements")
    party_at_statement_time = relationship("PoliticalParty")
    ai_analysis = relationship("AiAnalysis", back_populates="statement", uselist=False)
    media = relationship("MediaAsset", secondary="statement_media_assets", back_populates="statements")
