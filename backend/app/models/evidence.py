import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1000))
    archive_url: Mapped[str | None] = mapped_column(String(1000))
    source_type: Mapped[str] = mapped_column(String(80), default="other", index=True)
    publisher: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[date | None] = mapped_column(Date)
    accessed_at: Mapped[date | None] = mapped_column(Date)
    quote_or_relevant_excerpt: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    reliability_level: Mapped[str] = mapped_column(String(40), default="medium", index=True)
    source_origin: Mapped[str] = mapped_column(String(40), default="manual", index=True)
    structural_status: Mapped[str] = mapped_column(String(40), default="parsed", index=True)
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    created_from_ai_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_runs.id"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    fact_checked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    statement_claim_links = relationship("StatementClaimEvidenceLink", back_populates="evidence_item")
