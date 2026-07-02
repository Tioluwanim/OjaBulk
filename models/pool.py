import uuid
import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import Column, String, Numeric, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base

# This ensures relations are only imported by type checkers, preventing circular imports at runtime
if TYPE_CHECKING:
    from models.pool_contribution import PoolContribution
    from models.ledger_entry import LedgerEntry
    from models.payment import Payment


class PoolStatus(str, enum.Enum):
    OPEN = "open"
    FULFILLED = "fulfilled"
    REFUNDED = "refunded"


class Pool(Base):
    __tablename__ = "pools"

    # --- IDE Static Analysis Type Hints ---
    id: uuid.UUID
    title: str
    target_amount: Decimal
    current_locked_amount: Decimal
    supplier_name: str
    supplier_account_number: str
    supplier_bank_code: str
    status: PoolStatus
    deadline: datetime
    created_at: datetime
    fulfilled_at: datetime | None

    # Wrapped in quotes to resolve type definitions as forward references safely
    contributions: list["PoolContribution"]
    ledger_entries: list["LedgerEntry"]
    payments: list["Payment"]
    # --------------------------------------

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)

    target_amount = Column(Numeric(precision=18, scale=2), nullable=False)
    current_locked_amount = Column(Numeric(precision=18, scale=2), default=0, nullable=False)

    # Supplier payout details
    supplier_name = Column(String, nullable=False)
    supplier_account_number = Column(String, nullable=False)
    supplier_bank_code = Column(String, nullable=False)

    status = Column(Enum(PoolStatus), default=PoolStatus.OPEN, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    contributions = relationship("PoolContribution", back_populates="pool")
    ledger_entries = relationship("LedgerEntry", back_populates="pool")
    payments = relationship("Payment", back_populates="pool")