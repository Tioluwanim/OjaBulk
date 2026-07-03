import uuid
import enum

from sqlalchemy import (
    Column,
    Numeric,
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class ContributionStatus(str, enum.Enum):
    LOCKED = "locked"
    RELEASED = "released"   # Pool fulfilled → supplier paid
    REFUNDED = "refunded"   # Pool expired → returned to trader


class PoolContribution(Base):
    """
    Tracks how much a trader has contributed
    to a particular pool.

    This is the source of truth for locked funds.
    """

    __tablename__ = "pool_contributions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    trader_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "traders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    pool_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "pools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    amount_locked = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    status = Column(
        Enum(ContributionStatus),
        nullable=False,
        default=ContributionStatus.LOCKED,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # --------------------------------------------------
    # Relationships
    # --------------------------------------------------

    trader = relationship(
        "Trader",
        back_populates="pool_contributions",
    )

    pool = relationship(
        "Pool",
        back_populates="contributions",
    )

    # --------------------------------------------------
    # Constraints
    # --------------------------------------------------

    __table_args__ = (
        UniqueConstraint(
            "trader_id",
            "pool_id",
            name="uq_trader_pool_contribution",
        ),
        Index(
            "idx_pool_contributions_pool",
            "pool_id",
        ),
        Index(
            "idx_pool_contributions_trader",
            "trader_id",
        ),
        Index(
            "idx_pool_contributions_status",
            "status",
        ),
    )