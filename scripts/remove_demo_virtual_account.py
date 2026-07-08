import sys
from pathlib import Path

# Add the project root to path so we can import the app modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings
from core.database import SessionLocal
from models import Trader, Identity, IdentityRole


def _resolve_demo_traders(db) -> list[Trader]:
    """
    Resolve demo trader rows from the configured demo phone numbers.

    Some demo logins are stored as Identity rows that point at a
    different Trader phone number, so we try direct Trader.phone lookups
    first and then fall back to Identity.linked_trader_id.
    """
    resolved: dict[str, Trader] = {}

    for phone in settings.DEMO_PHONE_NUMBERS:
        trader = db.query(Trader).filter(Trader.phone == phone).first()
        if trader:
            resolved[str(trader.id)] = trader
            continue

        identity = db.query(Identity).filter(Identity.phone == phone).first()
        if not identity:
            print(f"No trader or identity found for demo phone {phone}")
            continue

        if identity.role != IdentityRole.TRADER or identity.linked_trader_id is None:
            print(
                f"Demo phone {phone} is registered as {identity.role.value} "
                "and has no linked trader row to clean up."
            )
            continue

        trader = db.query(Trader).filter(Trader.id == identity.linked_trader_id).first()
        if not trader:
            print(
                f"Demo phone {phone} points to trader id {identity.linked_trader_id}, "
                "but that trader row does not exist."
            )
            continue

        resolved[str(trader.id)] = trader
        print(
            f"Resolved demo phone {phone} via linked trader "
            f"{trader.phone} (identity: {identity.display_name})"
        )

    return list(resolved.values())


def remove_demo_virtual_account() -> None:
    db = SessionLocal()
    try:
        print(f"Clearing stored virtual account details for demo users: {settings.DEMO_PHONE_NUMBERS}")

        traders = _resolve_demo_traders(db)

        if not traders:
            print("No demo traders found in database.")
            return

        for trader in traders:
            if trader.virtual_account_number or trader.bank_name or trader.bank_account_name:
                print(f"Clearing virtual account data for {trader.phone} (trader ID: {trader.id})")
                trader.virtual_account_number = None
                trader.bank_name = None
                trader.bank_account_name = None
            else:
                print(f"No stored virtual account data for {trader.phone}")

        db.commit()
        print("Cleanup complete. The demo trader will need fresh provisioning before showing a real account.")

    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    remove_demo_virtual_account()