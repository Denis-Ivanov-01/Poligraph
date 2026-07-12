import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


program_media_assets = Table(
    "program_media_assets",
    Base.metadata,
    Column("program_id", ForeignKey("programs.id"), primary_key=True),
    Column("media_asset_id", ForeignKey("media_assets.id"), primary_key=True),
    Column("document_role", String(80), nullable=False, default="source_document"),
    Column("display_order", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    short_description: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    program_type: Mapped[str] = mapped_column(String(80), default="other", index=True)
    political_subject_name: Mapped[str | None] = mapped_column(String(255))
    related_party_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("political_parties.id"))
    related_coalition_name: Mapped[str | None] = mapped_column(String(255))
    period_text: Mapped[str | None] = mapped_column(String(160))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    publication_date: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_title: Mapped[str | None] = mapped_column(String(255))
    source_description: Mapped[str | None] = mapped_column(Text)
    source_acquisition_method: Mapped[str | None] = mapped_column(String(80), index=True)
    source_coverage_status: Mapped[str | None] = mapped_column(String(40), index=True)
    source_acquisition_note: Mapped[str | None] = mapped_column(Text)
    source_document_complete: Mapped[bool | None] = mapped_column()
    supplementary_source_urls: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(60), default="draft", index=True)
    structural_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    structural_review_note: Mapped[str | None] = mapped_column(Text)
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    factual_review_note: Mapped[str | None] = mapped_column(Text)
    is_active_government_program: Mapped[bool] = mapped_column(default=False, index=True)
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    structural_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    related_party = relationship("PoliticalParty", back_populates="programs")
    media = relationship("MediaAsset", secondary=program_media_assets)
    sections = relationship("ProgramSection", back_populates="program", cascade="all, delete-orphan")
    ai_extractions = relationship("ProgramAiExtraction", back_populates="program", cascade="all, delete-orphan")
    commitments = relationship("Commitment", back_populates="program", cascade="all, delete-orphan")


class ProgramSection(Base):
    __tablename__ = "program_sections"
    __table_args__ = (UniqueConstraint("program_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id"), index=True)
    parent_section_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("program_sections.id"), index=True)
    section_code: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(180), index=True)
    original_heading: Mapped[str | None] = mapped_column(String(255))
    original_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    problem_description: Mapped[str | None] = mapped_column(Text)
    aggregate_status_summary: Mapped[str | None] = mapped_column(Text)
    key_findings: Mapped[list | None] = mapped_column(JSONB)
    policy_area: Mapped[str | None] = mapped_column(String(160), index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    source_origin: Mapped[str] = mapped_column(String(40), default="manual", index=True)
    import_ref: Mapped[str | None] = mapped_column(String(80), index=True)
    structural_status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    program = relationship("Program", back_populates="sections")
    parent_section = relationship("ProgramSection", remote_side=[id], back_populates="child_sections")
    child_sections = relationship("ProgramSection", back_populates="parent_section", cascade="all, delete-orphan")
    commitments = relationship("Commitment", back_populates="program_section")


class ProgramAiExtraction(Base):
    __tablename__ = "program_ai_extractions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id"), index=True)
    ai_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_runs.id"), unique=True)
    extracted_commitments_count: Mapped[int | None] = mapped_column()
    extraction_summary: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[str] = mapped_column(String(40), default="needs_review", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    program = relationship("Program", back_populates="ai_extractions")
