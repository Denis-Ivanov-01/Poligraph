import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Commitment(Base):
    __tablename__ = "commitments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    original_text: Mapped[str] = mapped_column(Text)
    normalized_description: Mapped[str | None] = mapped_column(Text)
    political_subject_name: Mapped[str | None] = mapped_column(String(255))
    related_party_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("political_parties.id"))
    related_coalition_name: Mapped[str | None] = mapped_column(String(255))
    topic: Mapped[str | None] = mapped_column(String(160), index=True)
    responsible_institutions: Mapped[str | None] = mapped_column(Text)
    period: Mapped[str | None] = mapped_column(String(160))
    deadline: Mapped[date | None] = mapped_column(Date)
    measurable_criteria: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="not_started", index=True)
    status_group: Mapped[str] = mapped_column(String(80), default="active", index=True)
    status_explanation: Mapped[str | None] = mapped_column(Text)
    confidence_level: Mapped[str] = mapped_column(String(80), default="medium", index=True)
    confidence_explanation: Mapped[str | None] = mapped_column(Text)
    last_status_update: Mapped[date | None] = mapped_column(Date)
    is_key_commitment: Mapped[bool] = mapped_column(default=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    program = relationship("Program", back_populates="commitments")
    related_party = relationship("PoliticalParty", back_populates="commitments")
    evidence = relationship("CommitmentEvidence", back_populates="commitment", cascade="all, delete-orphan")


class CommitmentEvidence(Base):
    __tablename__ = "commitment_evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    commitment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("commitments.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(100), default="other", index=True)
    publisher: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[date | None] = mapped_column(Date)
    quote_or_relevant_excerpt: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    supports_status: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    commitment = relationship("Commitment", back_populates="evidence")
