import argparse
import sys
from pathlib import Path

# Add the project root to path so we can import the app modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings
from core.database import SessionLocal
from models import (
    Trader,
    Identity,
    IdentityRole,
    Payment,
    LedgerEntry,
    PoolContribution,
    EsusuContribution,
    EsusuMember,
)


def _selected_demo_phones(phone: str | None = None) -> list[str]:
    if phone:
        return [phone]
    return list(settings.DEMO_PHONE_NUMBERS)


def _resolve_demo_traders(db, phone_numbers: list[str]) -> list[Trader]:
    """
    Resolve demo trader rows from the configured demo phone numbers.

    Some demo logins are stored as Identity rows that point at a
    different Trader phone number, so we try direct Trader.phone lookups
    first and then fall back to Identity.linked_trader_id.
    """
    resolved: dict[str, Trader] = {}

    for phone in phone_numbers:
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


def _clear_demo_trader_data(db, trader: Trader) -> dict[str, int]:
    esusu_contributions_deleted = (
        db.query(EsusuContribution)
        .filter(EsusuContribution.trader_id == trader.id)
        .delete(synchronize_session=False)
    )

    esusu_members_deleted = (
        db.query(EsusuMember)
        .filter(EsusuMember.trader_id == trader.id)
        .delete(synchronize_session=False)
    )

    pool_contributions_deleted = (
        db.query(PoolContribution)
        .filter(PoolContribution.trader_id == trader.id)
        .delete(synchronize_session=False)
    )

    ledger_entries_deleted = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.trader_id == trader.id)
        .delete(synchronize_session=False)
    )

    payments_deleted = (
        db.query(Payment)
        .filter(Payment.trader_id == trader.id)
        .delete(synchronize_session=False)
    )

    trader.spendable_balance = 0
    trader.total_contributed = 0

    return {
        "esusu_contributions": esusu_contributions_deleted,
        "esusu_members": esusu_members_deleted,
        "pool_contributions": pool_contributions_deleted,
        "ledger_entries": ledger_entries_deleted,
        "payments": payments_deleted,
    }


def clear_demo_trader_data(phone: str | None = None) -> None:
    db = SessionLocal()
    try:
        phone_numbers = _selected_demo_phones(phone)
        print(f"Clearing demo trader data for phones: {phone_numbers}")

        traders = _resolve_demo_traders(db, phone_numbers)

        if not traders:
            print("No demo traders found in database.")
            return

        for trader in traders:
            print(f"Clearing demo history for {trader.phone} (trader ID: {trader.id})")
            counts = _clear_demo_trader_data(db, trader)
            print(
                "Deleted rows: "
                f"payments={counts['payments']}, "
                f"ledger_entries={counts['ledger_entries']}, "
                f"pool_contributions={counts['pool_contributions']}, "
                f"esusu_members={counts['esusu_members']}, "
                f"esusu_contributions={counts['esusu_contributions']}"
            )

        db.commit()
        print("Cleanup complete. Real virtual account details were preserved.")

    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        db.close()


def remove_demo_virtual_account() -> None:
    clear_demo_trader_data()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clear fake demo trader data while preserving the real virtual account."
    )
    parser.add_argument(
        "--phone",
        help="Optional demo trader phone number to clean up instead of all configured demo phones.",
    )
    args = parser.parse_args()
    clear_demo_trader_data(phone=args.phone)