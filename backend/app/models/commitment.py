import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Commitment(Base):
    __tablename__ = "commitments"
    __table_args__ = (UniqueConstraint("program_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id"), index=True)
    program_section_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("program_sections.id"))
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(160), index=True)
    original_text: Mapped[str | None] = mapped_column(Text)
    normalized_description: Mapped[str | None] = mapped_column(Text)
    political_subject_name: Mapped[str | None] = mapped_column(String(255))
    related_party_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("political_parties.id"))
    related_coalition_name: Mapped[str | None] = mapped_column(String(255))
    topic: Mapped[str | None] = mapped_column(String(160), index=True)
    responsible_institutions_text: Mapped[str | None] = mapped_column(Text)
    period: Mapped[str | None] = mapped_column(String(160))
    deadline: Mapped[date | None] = mapped_column(Date)
    measurable_criteria: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="not_started", index=True)
    status_group: Mapped[str] = mapped_column(String(80), default="active", index=True)
    status_explanation: Mapped[str | None] = mapped_column(Text)
    confidence_level: Mapped[str] = mapped_column(String(80), default="medium", index=True)
    confidence_explanation: Mapped[str | None] = mapped_column(Text)
    last_status_update: Mapped[date | None] = mapped_column(Date)
    materiality: Mapped[str] = mapped_column(String(40), default="medium", index=True)
    is_key_commitment: Mapped[bool] = mapped_column(default=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    structural_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    program = relationship("Program", back_populates="commitments")
    program_section = relationship("ProgramSection")
    related_party = relationship("PoliticalParty", back_populates="commitments")
    status_updates = relationship("CommitmentStatusUpdate", back_populates="commitment", cascade="all, delete-orphan")
    evidence_links = relationship("CommitmentEvidenceLink", back_populates="commitment", cascade="all, delete-orphan")
    evidence = relationship("CommitmentEvidenceLink", viewonly=True)

    @property
    def responsible_institutions(self) -> str | None:
        return self.responsible_institutions_text

    @responsible_institutions.setter
    def responsible_institutions(self, value: str | None) -> None:
        self.responsible_institutions_text = value


class CommitmentStatusUpdate(Base):
    __tablename__ = "commitment_status_updates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    commitment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("commitments.id"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(80))
    new_status: Mapped[str] = mapped_column(String(80))
    previous_status_group: Mapped[str | None] = mapped_column(String(80))
    new_status_group: Mapped[str] = mapped_column(String(80))
    update_date: Mapped[date] = mapped_column(Date)
    status_explanation: Mapped[str | None] = mapped_column(Text)
    confidence_level: Mapped[str] = mapped_column(String(40), default="medium")
    confidence_explanation: Mapped[str | None] = mapped_column(Text)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_runs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    commitment = relationship("Commitment", back_populates="status_updates")


class CommitmentEvidenceLink(Base):
    __tablename__ = "commitment_evidence_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    commitment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("commitments.id"), index=True)
    status_update_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("commitment_status_updates.id"))
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence_items.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(80), default="supports_status", index=True)
    note: Mapped[str | None] = mapped_column(Text)
    source_origin: Mapped[str] = mapped_column(String(40), default="manual")
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    commitment = relationship("Commitment", back_populates="evidence_links")
    evidence_item = relationship("EvidenceItem")

    @property
    def title(self) -> str:
        return self.evidence_item.title if self.evidence_item else ""

    @property
    def url(self) -> str | None:
        return self.evidence_item.url if self.evidence_item else None

    @property
    def source_type(self) -> str:
        return self.evidence_item.source_type if self.evidence_item else "other"

    @property
    def publisher(self) -> str | None:
        return self.evidence_item.publisher if self.evidence_item else None

    @property
    def published_at(self):
        return self.evidence_item.published_at if self.evidence_item else None

    @property
    def quote_or_relevant_excerpt(self) -> str | None:
        return self.evidence_item.quote_or_relevant_excerpt if self.evidence_item else None

    @property
    def description(self) -> str | None:
        return self.evidence_item.description if self.evidence_item else None

    @property
    def supports_status(self) -> bool:
        return self.relation_type in {"supports_status", "proves_completion", "proves_delay", "proves_violation"}


CommitmentEvidence = CommitmentEvidenceLink
