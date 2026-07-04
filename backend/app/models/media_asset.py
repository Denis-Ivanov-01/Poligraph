import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


statement_media_assets = Table(
    "statement_media_assets",
    Base.metadata,
    Column("statement_id", ForeignKey("statements.id"), primary_key=True),
    Column("media_asset_id", ForeignKey("media_assets.id"), primary_key=True),
)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    file_path: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[str] = mapped_column(String(80))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    statements = relationship("Statement", secondary=statement_media_assets, back_populates="media")
