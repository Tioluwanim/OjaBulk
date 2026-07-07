import uuid
import enum
from sqlalchemy import Column, String, Numeric, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base


class EntryType(str, enum.Enum):
    SPENDABLE_CREDIT      = "spendable_credit"
    POOL_LOCK             = "pool_lock"
    POOL_RELEASE_PAYOUT   = "pool_release_payout"
    POOL_REFUND           = "pool_refund"
    ESUSU_CONTRIBUTION    = "esusu_contribution"
    ESUSU_PAYOUT          = "esusu_payout"


class LedgerEntry(Base):
    """
    Immutable financial record. Every balance change produces one row here.
    No updated_at column — these rows are never modified after creation.
    This is the audit trail that makes OjaBulk's reconciliation report possible.
    """
    __tablename__ = "ledger_entries"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id = Column(UUID(as_uuid=True), ForeignKey("traders.id"), nullable=False)
    pool_id   = Column(UUID(as_uuid=True), ForeignKey("pools.id"), nullable=True)

    entry_type    = Column(Enum(EntryType), nullable=False)
    amount        = Column(Numeric(precision=18, scale=2), nullable=False)
    balance_after = Column(Numeric(precision=18, scale=2), nullable=False)
    note          = Column(String, nullable=True)

    # created_at only — no updated_at. These rows are immutable by design.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    trader = relationship("Trader", back_populates="ledger_entries")
    pool   = relationship("Pool", back_populates="ledger_entries")
