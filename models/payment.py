import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id = Column(UUID(as_uuid=True), ForeignKey("traders.id"), nullable=False)

    amount_received = Column(Numeric(precision=18, scale=2), nullable=False)

    # UNIQUE constraint — this is the idempotency guarantee
    # If Nomba delivers the same webhook twice, the second insert fails here
    # before any balance change can happen
    nomba_transaction_ref = Column(String, nullable=False, unique=True)

    spendable_portion = Column(Numeric(precision=18, scale=2), default=0)
    pool_portion      = Column(Numeric(precision=18, scale=2), default=0)
    pool_id           = Column(UUID(as_uuid=True), ForeignKey("pools.id"), nullable=True)

    received_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    trader = relationship("Trader", back_populates="payments")
    pool   = relationship("Pool", back_populates="payments")