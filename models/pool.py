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
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class PoolStatus(str, enum.Enum):
    OPEN = "open"
    # Target reached, Nomba transfer initiated but not yet confirmed
    # (transfer_service returned is_pending=True). Contributions stay
    # LOCKED and contributors are NOT told the payout is confirmed
    # until background/payout_finalizer.py requeries Nomba and finds
    # a final status.
    PAYOUT_PROCESSING = "payout_processing"
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

    # The market this pool belongs to. A Head of Traders may only
    # create pools where this matches their Identity.market_name —
    # enforced in routers/pools.py, not just a display field.
    market_name = Column(
        String,
        nullable=True,
    )

    # Which Identity created this pool (admin or head_of_traders).
    # Used to prove the market-scoping rule was actually enforced at
    # creation time, and for audit purposes.
    created_by_identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
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

    # Set when the wholesaler logs in and confirms they have received
    # the order / payout. This is a NEW piece of state — previously a
    # pool went straight from "fulfilled" to nothing. NULL means the
    # wholesaler has not yet confirmed, even if the pool is fulfilled
    # and the transfer succeeded on Nomba's side.
    wholesaler_confirmed_at = Column(
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

    created_by = relationship(
        "Identity",
        foreign_keys=[created_by_identity_id],
    )

    # --------------------------------------------------
    # Indexes
    # --------------------------------------------------

    __table_args__ = (
        Index("idx_pool_status", "status"),
        Index("idx_pool_deadline", "deadline"),
        Index("idx_pool_market", "market_name"),
    )