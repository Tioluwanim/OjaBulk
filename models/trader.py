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

    # Payout-destination bank account — DIFFERENT from
    # virtual_account_number above, which is an INBOUND-only receiving
    # account traders send money into. These three fields are where
    # OjaBulk sends money OUT to a trader (e.g. an Esusu/Ajo
    # beneficiary payout via services/transfers.py, the same Nomba
    # Transfer API used for Pool supplier payouts). All nullable and
    # optional: a trader who hasn't registered these yet still gets
    # paid, just credited to their in-app spendable_balance instead of
    # a real external bank transfer — see services/esusu.py's
    # _credit_beneficiary() for that fallback.
    payout_bank_code = Column(String, nullable=True)
    payout_account_number = Column(String, nullable=True)
    payout_account_name = Column(String, nullable=True)

    # Balances — always Numeric to avoid float rounding in financial data
    spendable_balance = Column(Numeric(precision=18, scale=2), default=0, nullable=False)
    total_contributed = Column(Numeric(precision=18, scale=2), default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    payments = relationship("Payment", back_populates="trader")
    ledger_entries = relationship("LedgerEntry", back_populates="trader")
    pool_contributions = relationship("PoolContribution", back_populates="trader")
