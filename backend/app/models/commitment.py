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
    program_section_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("program_sections.id"), index=True)
    parent_commitment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("commitments.id"))
    import_ref: Mapped[str | None] = mapped_column(String(80), index=True)
    display_code: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(160), index=True)
    original_text: Mapped[str | None] = mapped_column(Text)
    normalized_description: Mapped[str | None] = mapped_column(Text)
    political_subject_name: Mapped[str | None] = mapped_column(String(255))
    related_party_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("political_parties.id"))
    related_coalition_name: Mapped[str | None] = mapped_column(String(255))
    topic: Mapped[str | None] = mapped_column(String(160), index=True)
    responsible_institutions_text: Mapped[str | None] = mapped_column(Text)
    period_text: Mapped[str | None] = mapped_column(String(160))
    deadline: Mapped[date | None] = mapped_column(Date)
    measurable_criteria: Mapped[str | None] = mapped_column(Text)
    commitment_type: Mapped[str | None] = mapped_column(String(80), index=True)
    promised_item_type: Mapped[str | None] = mapped_column(String(80), index=True)
    baseline_mode: Mapped[str | None] = mapped_column(String(80), index=True)
    required_external_actors: Mapped[str | None] = mapped_column(Text)
    control_level: Mapped[str | None] = mapped_column(String(80), index=True)
    evaluation_basis: Mapped[str | None] = mapped_column(Text)
    contribution_types_text: Mapped[str | None] = mapped_column(Text)
    official_program_change_note: Mapped[str | None] = mapped_column(Text)
    source_version_note: Mapped[str | None] = mapped_column(Text)
    quantitative_target: Mapped[str | None] = mapped_column(Text)
    quantitative_actual: Mapped[str | None] = mapped_column(Text)
    measure_validity_status: Mapped[str | None] = mapped_column(String(80), index=True)
    current_status: Mapped[str] = mapped_column(String(80), default="not_started", index=True)
    status_group: Mapped[str] = mapped_column(String(80), default="pending", index=True)
    status_explanation: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(80), default="medium", index=True)
    confidence_explanation: Mapped[str | None] = mapped_column(Text)
    contribution_level: Mapped[str] = mapped_column(String(80), default="indeterminate", index=True)
    contribution_explanation: Mapped[str | None] = mapped_column(Text)
    contribution_confidence: Mapped[str | None] = mapped_column(String(80), index=True)
    last_status_update: Mapped[date | None] = mapped_column(Date)
    materiality: Mapped[str] = mapped_column(String(40), default="medium", index=True)
    materiality_reason: Mapped[str | None] = mapped_column(Text)
    importance_level: Mapped[str] = mapped_column(String(40), default="standard", index=True)
    importance_weight: Mapped[int] = mapped_column(Integer, default=2)
    is_key_commitment: Mapped[bool] = mapped_column(default=False, index=True)
    source_origin: Mapped[str] = mapped_column(String(40), default="manual", index=True)
    structural_status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    structural_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    program = relationship("Program", back_populates="commitments")
    program_section = relationship("ProgramSection", back_populates="commitments")
    parent_commitment = relationship("Commitment", remote_side=[id])
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

    @property
    def period(self) -> str | None:
        return self.period_text

    @period.setter
    def period(self, value: str | None) -> None:
        self.period_text = value

    @property
    def status(self) -> str:
        return self.current_status

    @status.setter
    def status(self, value: str) -> None:
        self.current_status = value

    @property
    def confidence_level(self) -> str:
        return self.confidence

    @confidence_level.setter
    def confidence_level(self, value: str) -> None:
        self.confidence = value


class CommitmentStatusUpdate(Base):
    __tablename__ = "commitment_status_updates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    commitment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("commitments.id"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(80))
    new_status: Mapped[str] = mapped_column(String(80))
    previous_status_group: Mapped[str | None] = mapped_column(String(80))
    new_status_group: Mapped[str] = mapped_column(String(80))
    previous_contribution_level: Mapped[str | None] = mapped_column(String(80))
    new_contribution_level: Mapped[str | None] = mapped_column(String(80))
    effective_date: Mapped[date | None] = mapped_column(Date)
    status_explanation: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(40), default="medium")
    confidence_explanation: Mapped[str | None] = mapped_column(Text)
    contribution_explanation: Mapped[str | None] = mapped_column(Text)
    contribution_confidence: Mapped[str | None] = mapped_column(String(40))
    update_reason: Mapped[str | None] = mapped_column(Text)
    source_origin: Mapped[str] = mapped_column(String(40), default="manual")
    structural_status: Mapped[str] = mapped_column(String(40), default="parsed")
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed")
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_runs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    commitment = relationship("Commitment", back_populates="status_updates")
    ai_run = relationship("AiRun", foreign_keys=[ai_run_id])

    @property
    def update_date(self) -> date | None:
        return self.effective_date

    @update_date.setter
    def update_date(self, value: date | None) -> None:
        self.effective_date = value

    @property
    def confidence_level(self) -> str:
        return self.confidence

    @confidence_level.setter
    def confidence_level(self, value: str) -> None:
        self.confidence = value


class CommitmentEvidenceLink(Base):
    __tablename__ = "commitment_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "status_update_id",
            "evidence_item_id",
            "relation_type",
            name="uq_commitment_evidence_link_update_evidence_relation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    commitment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("commitments.id"), index=True)
    status_update_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("commitment_status_updates.id"))
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence_items.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(80), default="supports_status", index=True)
    evidence_role: Mapped[str | None] = mapped_column(String(80), index=True)
    evidence_strength: Mapped[str | None] = mapped_column(String(40), index=True)
    is_self_reported: Mapped[bool] = mapped_column(default=False, index=True)
    is_independent_confirmation: Mapped[bool] = mapped_column(default=False, index=True)
    is_contradictory: Mapped[bool] = mapped_column(default=False, index=True)
    is_disproven: Mapped[bool] = mapped_column(default=False, index=True)
    limitations: Mapped[str | None] = mapped_column(Text)
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
