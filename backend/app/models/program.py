import uuid
from datetime import date, datetime
from typing import ClassVar

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Program(Base):
    __tablename__ = "programs"

    generated_prompt_text: ClassVar[str | None] = None
    raw_ai_response: ClassVar[str | None] = None

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    program_type: Mapped[str] = mapped_column(String(80), default="other", index=True)
    political_subject_name: Mapped[str | None] = mapped_column(String(255))
    related_party_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("political_parties.id"))
    related_coalition_name: Mapped[str | None] = mapped_column(String(255))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_title: Mapped[str | None] = mapped_column(String(255))
    source_description: Mapped[str | None] = mapped_column(Text)
    is_active_government_program: Mapped[bool] = mapped_column(default=False, index=True)
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    structural_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    related_party = relationship("PoliticalParty", back_populates="programs")
    sections = relationship("ProgramSection", back_populates="program", cascade="all, delete-orphan")
    ai_extractions = relationship("ProgramAiExtraction", back_populates="program", cascade="all, delete-orphan")
    commitments = relationship("Commitment", back_populates="program", cascade="all, delete-orphan")


class ProgramSection(Base):
    __tablename__ = "program_sections"
    __table_args__ = (UniqueConstraint("program_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(180), index=True)
    original_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    program = relationship("Program", back_populates="sections")


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
