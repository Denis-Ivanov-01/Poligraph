import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


statement_media_assets = Table(
    "statement_media_assets",
    Base.metadata,
    Column("statement_id", ForeignKey("statements.id"), primary_key=True),
    Column("media_asset_id", ForeignKey("media_assets.id"), primary_key=True),
    Column("display_order", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    file_path: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[str] = mapped_column(String(80))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(120))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    statements = relationship("Statement", secondary=statement_media_assets, back_populates="media")
