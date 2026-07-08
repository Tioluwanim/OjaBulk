import argparse
import sys
from pathlib import Path

# Add the project root to path so we can import the app modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings
from core.database import SessionLocal
from models import Trader, Identity, IdentityRole
from services.virtual_accounts import virtual_account_service


def _default_demo_phone() -> str:
    if settings.DEMO_PHONE_NUMBERS:
        return settings.DEMO_PHONE_NUMBERS[0]
    return "08099999001"


def _resolve_demo_trader(db, phone: str) -> Trader | None:
    trader = db.query(Trader).filter(Trader.phone == phone).first()
    if trader:
        return trader

    identity = db.query(Identity).filter(Identity.phone == phone).first()
    if not identity:
        return None

    if identity.role != IdentityRole.TRADER or identity.linked_trader_id is None:
        return None

    return db.query(Trader).filter(Trader.id == identity.linked_trader_id).first()


def provision_real_virtual_account(phone: str) -> None:
    db = SessionLocal()
    try:
        trader = _resolve_demo_trader(db, phone)
        if not trader:
            print(f"No trader found for phone {phone}")
            return

        if trader.phone != phone:
            print(f"Resolved demo phone {phone} to linked trader {trader.phone}")

        print(f"Provisioning real Nomba virtual account for {trader.phone} ({trader.name})")
        account = virtual_account_service.create(
            trader_id=str(trader.id),
            trader_name=trader.name,
        )

        trader.virtual_account_number = account.get("bank_account_number")
        trader.bank_name = account.get("bank_name")
        trader.bank_account_name = account.get("bank_account_name")

        db.commit()

        print("Provisioning complete")
        print(f"Account number: {trader.virtual_account_number}")
        print(f"Bank name: {trader.bank_name}")
        print(f"Account name: {trader.bank_account_name}")

    except Exception as e:
        db.rollback()
        print(f"Error during provisioning: {e}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision a real Nomba virtual account for the demo trader."
    )
    parser.add_argument(
        "--phone",
        default=_default_demo_phone(),
        help="Trader phone number in canonical 0XXXXXXXXXX format.",
    )
    args = parser.parse_args()
    provision_real_virtual_account(args.phone)


if __name__ == "__main__":
    main()