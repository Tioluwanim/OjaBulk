import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    Enum,
    Integer,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class PoolStatus(str, enum.Enum):
    OPEN = "open"
    FULFILLED = "fulfilled"
    REFUNDED = "refunded"


class Pool(Base):
    """
    Group-buying pool.

    Money is locked here until either:

    1. Target amount is reached → payout
    2. Deadline expires → refund
    """

    __tablename__ = "pools"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # --------------------------------------------------
    # Basic Information
    # --------------------------------------------------

    title = Column(
        String,
        nullable=False,
    )

    description = Column(
        String,
        nullable=True,
    )

    # --------------------------------------------------
    # Funding
    # --------------------------------------------------

    target_amount = Column(
        Numeric(18, 2),
        nullable=False,
    )

    current_locked_amount = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    fulfilled_amount = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    minimum_contributors = Column(
        Integer,
        nullable=False,
        default=1,
    )

    # --------------------------------------------------
    # Supplier
    # --------------------------------------------------

    supplier_name = Column(
        String,
        nullable=False,
    )

    supplier_account_number = Column(
        String,
        nullable=False,
    )

    supplier_bank_code = Column(
        String,
        nullable=False,
    )

    # --------------------------------------------------
    # Nomba Transfer Tracking
    # --------------------------------------------------

    nomba_transfer_ref = Column(
        String,
        nullable=True,
    )

    # --------------------------------------------------
    # Lifecycle
    # --------------------------------------------------

    status = Column(
        Enum(PoolStatus),
        nullable=False,
        default=PoolStatus.OPEN,
    )

    deadline = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    fulfilled_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    refunded_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --------------------------------------------------
    # Relationships
    # --------------------------------------------------

    contributions = relationship(
        "PoolContribution",
        back_populates="pool",
        cascade="all, delete-orphan",
    )

    ledger_entries = relationship(
        "LedgerEntry",
        back_populates="pool",
        cascade="all, delete-orphan",
    )

    payments = relationship(
        "Payment",
        back_populates="pool",
    )

    # --------------------------------------------------
    # Indexes
    # --------------------------------------------------

    __table_args__ = (
        Index("idx_pool_status", "status"),
        Index("idx_pool_deadline", "deadline"),
    )