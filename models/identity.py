"""
models/identity.py

The authentication + role layer for OjaBulk.

WHY THIS EXISTS (not a User table by default, but genuinely needed here):
    OjaBulk has three distinct actors who all need to log in by phone/OTP:
        - trader: an ordinary market trader (already modeled in Trader,
          but Trader itself has no login mechanism — this adds one)
        - head_of_traders: elevated visibility + pool creation, but
          SCOPED to their own market only (see market_name below)
        - wholesaler: sees only pools where they are the named supplier,
          and can confirm order receipt

    Identity is deliberately separate from Trader, not a replacement
    for it. A Trader row still tracks balances, virtual account, and
    ledger history — that has nothing to do with authentication.
    Identity is purely "who is allowed to log in, and what can they do."

    An Identity with role=trader is linked to exactly one Trader row
    (linked_trader_id) — logging in as that Identity lets them view
    their own Trader's balance and pool history. An Identity with
    role=head_of_traders or role=wholesaler has no linked Trader row,
    since they are not themselves contributing money.
"""

import uuid
import enum

from sqlalchemy import (
    Column,
    String,
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


class IdentityRole(str, enum.Enum):
    TRADER = "trader"
    HEAD_OF_TRADERS = "head_of_traders"
    WHOLESALER = "wholesaler"


class Identity(Base):
    """
    One row per person who can log in — trader, head of traders, or
    wholesaler. Identified by phone number, authenticated via OTP
    (see models/otp_session.py), not a password.
    """

    __tablename__ = "identities"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    phone = Column(
        String,
        nullable=False,
        unique=True,
    )

    display_name = Column(
        String,
        nullable=False,
    )

    role = Column(
        Enum(IdentityRole),
        nullable=False,
    )

    # --------------------------------------------------
    # Role-specific scoping fields
    # --------------------------------------------------

    # Meaningful for TRADER and HEAD_OF_TRADERS only.
    # For HEAD_OF_TRADERS, this is the market they are allowed to
    # create pools for — every pool-creation check validates against
    # this field, never against a market_name typed in the request.
    market_name = Column(
        String,
        nullable=True,
    )

    # Meaningful for TRADER only — links this login identity to their
    # existing Trader row (balances, virtual account, ledger).
    linked_trader_id = Column(
        UUID(as_uuid=True),
        ForeignKey("traders.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Meaningful for WHOLESALER only — the business name shown on
    # pools where they are the named supplier. This is intentionally
    # a plain string, not a link to Pool.supplier_name — a wholesaler
    # identity is created once and matched to pools by phone number
    # at login time (see routers/wholesalers.py), not by a rigid FK,
    # since the same wholesaler may supply many pools over time.
    business_name = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # --------------------------------------------------
    # Relationships
    # --------------------------------------------------

    linked_trader = relationship(
        "Trader",
        foreign_keys=[linked_trader_id],
    )

    # --------------------------------------------------
    # Constraints
    # --------------------------------------------------

    __table_args__ = (
        Index("idx_identity_phone", "phone"),
        Index("idx_identity_role", "role"),
        Index("idx_identity_market", "market_name"),
    )
