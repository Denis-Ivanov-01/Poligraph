import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AiRun(Base):
    __tablename__ = "ai_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    target_type: Mapped[str] = mapped_column(String(80), index=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    task_type: Mapped[str] = mapped_column(String(80), index=True)
    execution_mode: Mapped[str] = mapped_column(String(40), default="manual_external")
    status: Mapped[str] = mapped_column(String(80), default="prompt_generated", index=True)
    model_name: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(80))
    schema_version: Mapped[str] = mapped_column(String(80))
    prompt_text: Mapped[str] = mapped_column(Text)
    raw_ai_response: Mapped[str | None] = mapped_column(Text)
    parsed_json: Mapped[dict | None] = mapped_column(JSONB)
    parse_error: Mapped[str | None] = mapped_column(Text)
    structural_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    structural_review_note: Mapped[str | None] = mapped_column(Text)
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    factual_review_note: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    response_pasted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    structural_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    fact_checked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    response_pasted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    structural_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fact_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    statement_analysis = relationship("StatementAiAnalysis", back_populates="ai_run", uselist=False)
    created_by_user = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_ai_runs")


class StatementAiAnalysis(Base):
    __tablename__ = "statement_ai_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    statement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("statements.id"), index=True)
    ai_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_runs.id"), unique=True)
    analysis_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    factual_accuracy_applicability: Mapped[str] = mapped_column(String(40), default="applicable")
    factual_accuracy_score: Mapped[int | None] = mapped_column(Integer)
    logical_consistency_score: Mapped[int | None] = mapped_column(Integer)
    communicational_integrity_score: Mapped[int | None] = mapped_column(Integer)
    principle_consistency_score: Mapped[int | None] = mapped_column(Integer)
    factual_accuracy_explanation: Mapped[str | None] = mapped_column(Text)
    logical_consistency_explanation: Mapped[str | None] = mapped_column(Text)
    communicational_integrity_explanation: Mapped[str | None] = mapped_column(Text)
    principle_consistency_explanation: Mapped[str | None] = mapped_column(Text)
    evidence_review_completeness: Mapped[str] = mapped_column(String(80), default="partial")
    human_review_recommended: Mapped[bool] = mapped_column(default=False)
    human_review_reason: Mapped[str | None] = mapped_column(Text)
    structural_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    structural_review_note: Mapped[str | None] = mapped_column(Text)
    structural_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    structural_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    factual_review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", index=True)
    factual_review_note: Mapped[str | None] = mapped_column(Text)
    fact_checked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    fact_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_published: Mapped[bool] = mapped_column(default=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    statement = relationship("Statement", back_populates="ai_analysis")
    ai_run = relationship("AiRun", back_populates="statement_analysis")
    claims = relationship("StatementClaim", back_populates="statement_ai_analysis", cascade="all, delete-orphan")

    @property
    def model_name(self) -> str | None:
        return self.ai_run.model_name if self.ai_run else None

    @property
    def prompt_version(self) -> str | None:
        return self.ai_run.prompt_version if self.ai_run else None

    @property
    def schema_version(self) -> str | None:
        return self.ai_run.schema_version if self.ai_run else None

    @property
    def prompt_text(self) -> str:
        return self.ai_run.prompt_text if self.ai_run else ""

    @property
    def raw_ai_response(self) -> str:
        return self.ai_run.raw_ai_response if self.ai_run and self.ai_run.raw_ai_response else ""

    @property
    def source_urls(self) -> list[dict]:
        items = []
        seen = set()
        for claim in self.claims:
            for link in claim.evidence_links:
                evidence = link.evidence_item
                if evidence and evidence.id not in seen:
                    seen.add(evidence.id)
                    items.append({"url": evidence.url, "description": evidence.description or evidence.title})
        return items

    @property
    def overall_score(self) -> int | None:
        scores = [
            self.factual_accuracy_score,
            self.logical_consistency_score,
            self.communicational_integrity_score,
            self.principle_consistency_score,
        ]
        values = [score for score in scores if score is not None]
        return round(sum(values) / len(values)) if values else None

    @property
    def overall_explanation(self) -> str:
        return "Computed from the four dimension scores; not stored in the database."


AiAnalysis = StatementAiAnalysis
