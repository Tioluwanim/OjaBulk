"""
services/trader_registration.py

Shared trader registration logic -- used by both POST /traders
(routers/traders.py) and the interactive USSD registration flow
(services/ussd.py), so there is exactly one place that creates a
Trader + provisions their Nomba virtual account + creates their
Identity, instead of two implementations that could drift apart.
"""

from sqlalchemy.orm import Session

from models.trader import Trader
from models.identity import Identity, IdentityRole
from services.virtual_accounts import virtual_account_service


class TraderRegistrationError(Exception):
    """Raised for any registration failure the caller should surface
    as a user-facing message -- phone already registered, virtual
    account provisioning failed, etc."""
    pass


def register_trader(
    db: Session,
    name: str,
    phone: str,
    stall_number: str,
    market_name: str,
) -> Trader:
    """
    Creates a Trader, provisions their Nomba virtual account, and
    creates the linked Identity row so they can log in via OTP --
    identical to routers/traders.py's POST /traders, just callable
    directly instead of only over HTTP.

    Raises TraderRegistrationError for anything the caller should
    show back to the person registering (duplicate phone, virtual
    account provisioning failure).
    """
    existing = db.query(Trader).filter(Trader.phone == phone).first()
    if existing:
        raise TraderRegistrationError(
            f"A trader with phone {phone} already exists."
        )

    existing_identity = db.query(Identity).filter(
        Identity.phone == phone
    ).first()
    if existing_identity:
        raise TraderRegistrationError(
            f"This phone number is already registered as "
            f"{existing_identity.role.value}. A phone number can "
            f"only be linked to one role."
        )

    trader = Trader(
        name=name,
        phone=phone,
        stall_number=stall_number,
        market_name=market_name,
    )
    db.add(trader)
    db.flush()   # Get the UUID before calling Nomba

    try:
        account = virtual_account_service.create(
            trader_id=str(trader.id),
            trader_name=name,
        )
        trader.virtual_account_number = account["bank_account_number"]
        trader.bank_name              = account["bank_name"]
        trader.bank_account_name      = account["bank_account_name"]
    except Exception as e:
        db.rollback()
        raise TraderRegistrationError(
            f"Virtual account provisioning failed: {e}"
        )

    identity = Identity(
        phone=phone,
        display_name=name,
        role=IdentityRole.TRADER,
        market_name=market_name,
        linked_trader_id=trader.id,
    )
    db.add(identity)

    db.commit()
    db.refresh(trader)

    return trader
