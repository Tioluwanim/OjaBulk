import enum
import uuid

from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    Enum,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class EsusuStatus(str, enum.Enum):
    OPEN = "open"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EsusuRoundStatus(str, enum.Enum):
    OPEN = "open"
    PAID = "paid"


class EsusuCycle(Base):
    __tablename__ = "esusu_cycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    market_name = Column(String, nullable=True)

    contribution_amount = Column(Numeric(18, 2), nullable=False)
    total_members = Column(Integer, nullable=False)
    frequency_days = Column(Integer, nullable=False, default=7)

    current_round_number = Column(Integer, nullable=False, default=1)
    total_collected = Column(Numeric(18, 2), nullable=False, default=0)

    status = Column(Enum(EsusuStatus), nullable=False, default=EsusuStatus.OPEN)

    created_by_identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    activated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_by = relationship("Identity", foreign_keys=[created_by_identity_id])
    members = relationship(
        "EsusuMember",
        back_populates="cycle",
        cascade="all, delete-orphan",
    )
    rounds = relationship(
        "EsusuRound",
        back_populates="cycle",
        cascade="all, delete-orphan",
    )
    contributions = relationship(
        "EsusuContribution",
        back_populates="cycle",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_esusu_cycle_status", "status"),
        Index("idx_esusu_cycle_market", "market_name"),
    )


class EsusuMember(Base):
    __tablename__ = "esusu_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    cycle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("esusu_cycles.id", ondelete="CASCADE"),
        nullable=False,
    )
    trader_id = Column(
        UUID(as_uuid=True),
        ForeignKey("traders.id", ondelete="CASCADE"),
        nullable=False,
    )

    payout_position = Column(Integer, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_contributed_round = Column(Integer, nullable=True)
    last_received_round = Column(Integer, nullable=True)

    trader = relationship("Trader")
    cycle = relationship("EsusuCycle", back_populates="members")

    __table_args__ = (
        UniqueConstraint("cycle_id", "trader_id", name="uq_esusu_member_trader_cycle"),
        UniqueConstraint("cycle_id", "payout_position", name="uq_esusu_member_position_cycle"),
        Index("idx_esusu_member_cycle", "cycle_id"),
    )


class EsusuRound(Base):
    __tablename__ = "esusu_rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    cycle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("esusu_cycles.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_number = Column(Integer, nullable=False)
    beneficiary_member_id = Column(
        UUID(as_uuid=True),
        ForeignKey("esusu_members.id", ondelete="CASCADE"),
        nullable=False,
    )

    target_amount = Column(Numeric(18, 2), nullable=False)
    collected_amount = Column(Numeric(18, 2), nullable=False, default=0)
    status = Column(Enum(EsusuRoundStatus), nullable=False, default=EsusuRoundStatus.OPEN)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    cycle = relationship("EsusuCycle", back_populates="rounds")
    beneficiary_member = relationship("EsusuMember")
    contributions = relationship(
        "EsusuContribution",
        back_populates="round",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("cycle_id", "round_number", name="uq_esusu_round_cycle_number"),
        Index("idx_esusu_round_cycle", "cycle_id"),
    )


class EsusuContribution(Base):
    __tablename__ = "esusu_contributions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    cycle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("esusu_cycles.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_id = Column(
        UUID(as_uuid=True),
        ForeignKey("esusu_rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    trader_id = Column(
        UUID(as_uuid=True),
        ForeignKey("traders.id", ondelete="CASCADE"),
        nullable=False,
    )

    amount = Column(Numeric(18, 2), nullable=False)
    contributed_at = Column(DateTime(timezone=True), server_default=func.now())

    cycle = relationship("EsusuCycle", back_populates="contributions")
    round = relationship("EsusuRound", back_populates="contributions")
    trader = relationship("Trader")

    __table_args__ = (
        UniqueConstraint("round_id", "trader_id", name="uq_esusu_round_trader"),
        Index("idx_esusu_contribution_cycle", "cycle_id"),
        Index("idx_esusu_contribution_round", "round_id"),
    )