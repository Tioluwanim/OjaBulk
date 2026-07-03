import uuid
from sqlalchemy import Column, String, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base


class Trader(Base):
    __tablename__ = "traders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True)
    stall_number = Column(String, nullable=False)
    market_name = Column(String, nullable=False)

    # Nomba virtual account details — set after provisioning
    virtual_account_number = Column(String, unique=True, nullable=True)
    bank_name = Column(String, nullable=True)
    bank_account_name = Column(String, nullable=True)

    # Balances — always Numeric to avoid float rounding in financial data
    spendable_balance = Column(Numeric(precision=18, scale=2), default=0, nullable=False)
    total_contributed = Column(Numeric(precision=18, scale=2), default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    payments = relationship("Payment", back_populates="trader")
    ledger_entries = relationship("LedgerEntry", back_populates="trader")
    pool_contributions = relationship("PoolContribution", back_populates="trader")
