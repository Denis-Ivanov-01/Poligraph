import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StatementClaim(Base):
    __tablename__ = "statement_claims"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    statement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("statements.id"), index=True)
    statement_ai_analysis_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("statement_ai_analyses.id"), index=True)
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_runs.id"), index=True)
    import_ref: Mapped[str | None] = mapped_column(String(80), index=True)
    display_code: Mapped[str | None] = mapped_column(String(80))
    exact_quote: Mapped[str] = mapped_column(Text)
    normalized_claim: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(60), index=True)
    checkability: Mapped[str] = mapped_column(String(60), index=True)
    materiality: Mapped[str] = mapped_column(String(40), index=True)
    materiality_reason: Mapped[str | None] = mapped_column(Text)
    ai_verification_status: Mapped[str] = mapped_column(String(80), index=True)
    confidence_level: Mapped[str] = mapped_column(String(40), index=True)
    evidence_summary: Mapped[str | None] = mapped_column(Text)
    missing_or_uncertain_evidence: Mapped[str | None] = mapped_column(Text)
    used_for_dimensions_json: Mapped[list | None] = mapped_column(JSONB)
    source_origin: Mapped[str] = mapped_column(String(40), default="ai_imported", index=True)
    structural_status: Mapped[str] = mapped_column(String(40), default="parsed", index=True)
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    structural_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    fact_checked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    statement = relationship("Statement", back_populates="claims")
    statement_ai_analysis = relationship("StatementAiAnalysis", back_populates="claims")
    evidence_links = relationship("StatementClaimEvidenceLink", back_populates="claim", cascade="all, delete-orphan")


class StatementClaimEvidenceLink(Base):
    __tablename__ = "statement_claim_evidence_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("statement_claims.id"), index=True)
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence_items.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(40), default="supports", index=True)
    note: Mapped[str | None] = mapped_column(Text)
    source_origin: Mapped[str] = mapped_column(String(40), default="ai_imported", index=True)
    structural_status: Mapped[str] = mapped_column(String(40), default="parsed", index=True)
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    fact_checked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("StatementClaim", back_populates="evidence_links")
    evidence_item = relationship("EvidenceItem", back_populates="statement_claim_links")
