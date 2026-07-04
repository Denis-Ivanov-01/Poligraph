import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PartyMembership(Base):
    __tablename__ = "party_memberships"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    politician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("politicians.id"))
    party_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("political_parties.id"))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    politician = relationship("Politician", back_populates="memberships")
    party = relationship("PoliticalParty", back_populates="memberships")
