import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AiAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    statement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("statements.id"), unique=True)
    model_name: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(80))
    schema_version: Mapped[str] = mapped_column(String(80))
    analysis_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    factual_accuracy_score: Mapped[int] = mapped_column(Integer)
    logical_consistency_score: Mapped[int] = mapped_column(Integer)
    communicational_integrity_score: Mapped[int] = mapped_column(Integer)
    principle_consistency_score: Mapped[int] = mapped_column(Integer)
    overall_score: Mapped[int] = mapped_column(Integer)
    factual_accuracy_explanation: Mapped[str] = mapped_column(Text)
    logical_consistency_explanation: Mapped[str] = mapped_column(Text)
    communicational_integrity_explanation: Mapped[str] = mapped_column(Text)
    principle_consistency_explanation: Mapped[str] = mapped_column(Text)
    overall_explanation: Mapped[str] = mapped_column(Text)
    prompt_text: Mapped[str] = mapped_column(Text)
    raw_ai_response: Mapped[str] = mapped_column(Text)
    source_urls: Mapped[list[dict] | None] = mapped_column(JSONB)
    is_published: Mapped[bool] = mapped_column(default=False)

    statement = relationship("Statement", back_populates="ai_analysis")
