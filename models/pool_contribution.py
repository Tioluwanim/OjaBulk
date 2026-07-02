import uuid
import enum
from sqlalchemy import Column, Numeric, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base


class ContributionStatus(str, enum.Enum):
    LOCKED   = "locked"
    RELEASED = "released"   # Released to supplier on pool fulfillment
    REFUNDED = "refunded"   # Returned to spendable on pool failure


class PoolContribution(Base):
    __tablename__ = "pool_contributions"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id = Column(UUID(as_uuid=True), ForeignKey("traders.id"), nullable=False)
    pool_id   = Column(UUID(as_uuid=True), ForeignKey("pools.id"), nullable=False)

    amount_locked = Column(Numeric(precision=18, scale=2), nullable=False)
    status        = Column(Enum(ContributionStatus), default=ContributionStatus.LOCKED, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    trader = relationship("Trader", back_populates="pool_contributions")
    pool   = relationship("Pool", back_populates="contributions")