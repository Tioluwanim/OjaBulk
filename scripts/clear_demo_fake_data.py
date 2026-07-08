import argparse
import sys
from pathlib import Path

from sqlalchemy import or_, desc

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
    EsusuRound,
    EsusuCycle,
)


def _resolve_demo_trader(db, phone: str) -> tuple[Trader | None, Identity | None]:
    trader = db.query(Trader).filter(Trader.phone == phone).first()
    if trader:
        identity = db.query(Identity).filter(Identity.phone == phone).first()
        return trader, identity

    identity = db.query(Identity).filter(Identity.phone == phone).first()
    if not identity:
        return None, None

    if identity.role != IdentityRole.TRADER or identity.linked_trader_id is None:
        return None, identity

    trader = db.query(Trader).filter(Trader.id == identity.linked_trader_id).first()
    return trader, identity


def _default_demo_phone() -> str:
    if settings.DEMO_PHONE_NUMBERS:
        return settings.DEMO_PHONE_NUMBERS[0]
    return "08099999001"


FAKE_PAYMENT_PREFIXES = ("SEED", "FAKE", "TEST", "DEMO")
FAKE_NOTE_KEYWORDS = ("seed", "fake", "demo", "test")


def _is_fake_reference(reference: str) -> bool:
    upper_ref = reference.upper()
    return any(upper_ref.startswith(prefix) for prefix in FAKE_PAYMENT_PREFIXES)


def _seed_payment_query(db, trader: Trader):
    return (
        db.query(Payment)
        .filter(Payment.trader_id == trader.id)
        .filter(
            or_(
                *[Payment.nomba_transaction_ref.ilike(f"{prefix}%") for prefix in FAKE_PAYMENT_PREFIXES],
                Payment.nomba_transaction_ref == None,  # noqa: E711
            )
        )
    )


def _delete_older_rows(db, trader: Trader, identity: Identity | None, keep_transaction_ref: str | None) -> dict[str, int]:
    cycle_ids = []
    if identity is not None:
        cycle_ids = [
            row.id
            for row in db.query(EsusuCycle.id)
            .filter(EsusuCycle.created_by_identity_id == identity.id)
            .all()
        ]

    fake_payments = _seed_payment_query(db, trader)
    if keep_transaction_ref:
        fake_payments = fake_payments.filter(Payment.nomba_transaction_ref != keep_transaction_ref)

    fake_payment_ids = [row.id for row in fake_payments.all()]
    if not fake_payment_ids:
        payment_deleted = 0
    else:
        payment_deleted = (
            db.query(Payment)
            .filter(Payment.id.in_(fake_payment_ids))
            .delete(synchronize_session=False)
        )

    fake_ledger_ids = [
        row.id
        for row in db.query(LedgerEntry.id)
        .filter(
            LedgerEntry.trader_id == trader.id,
            or_(
                *[LedgerEntry.note.ilike(f"%{keyword}%") for keyword in FAKE_NOTE_KEYWORDS],
                LedgerEntry.note == None,  # noqa: E711
            )
        )
        .all()
    ]

    ledger_deleted = 0
    if fake_ledger_ids:
        ledger_deleted = (
            db.query(LedgerEntry)
            .filter(LedgerEntry.id.in_(fake_ledger_ids))
            .delete(synchronize_session=False)
        )

    pool_contrib_deleted = (
        db.query(PoolContribution)
        .filter(PoolContribution.trader_id == trader.id)
        .delete(synchronize_session=False)
    )

    esusu_contrib_deleted = (
        db.query(EsusuContribution)
        .filter(EsusuContribution.trader_id == trader.id)
        .delete(synchronize_session=False)
    )

    esusu_member_deleted = (
        db.query(EsusuMember)
        .filter(EsusuMember.trader_id == trader.id)
        .delete(synchronize_session=False)
    )

    esusu_round_deleted = 0
    if cycle_ids:
        esusu_round_deleted = (
            db.query(EsusuRound)
            .filter(EsusuRound.cycle_id.in_(cycle_ids))
            .delete(synchronize_session=False)
        )

    esusu_cycle_deleted = (
        db.query(EsusuCycle)
        .filter(EsusuCycle.created_by_identity_id == getattr(identity, "id", None))
        .delete(synchronize_session=False)
    )

    return {
        "payments": payment_deleted,
        "ledger_entries": ledger_deleted,
        "pool_contributions": pool_contrib_deleted,
        "esusu_contributions": esusu_contrib_deleted,
        "esusu_rounds": esusu_round_deleted,
        "esusu_members": esusu_member_deleted,
        "esusu_cycles": esusu_cycle_deleted,
    }


def _rebuild_trader_balance(db, trader: Trader) -> None:
    latest_ledger = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.trader_id == trader.id)
        .order_by(desc(LedgerEntry.created_at), desc(LedgerEntry.id))
        .first()
    )

    if latest_ledger:
        trader.spendable_balance = float(latest_ledger.balance_after)
    else:
        remaining_payments = (
            db.query(Payment)
            .filter(Payment.trader_id == trader.id)
            .all()
        )
        trader.spendable_balance = float(
            sum(float(payment.spendable_portion or 0) for payment in remaining_payments)
        )

    trader.total_contributed = float(
        sum(
            float(payment.amount_received or 0)
            for payment in db.query(Payment).filter(Payment.trader_id == trader.id).all()
        )
    )


def _recalculate_from_latest_non_fake_payment(db, trader: Trader) -> None:
    latest_real_payment = (
        db.query(Payment)
        .filter(Payment.trader_id == trader.id)
        .filter(~Payment.nomba_transaction_ref.ilike("SEED%"))
        .filter(~Payment.nomba_transaction_ref.ilike("FAKE%"))
        .filter(~Payment.nomba_transaction_ref.ilike("TEST%"))
        .filter(~Payment.nomba_transaction_ref.ilike("DEMO%"))
        .order_by(desc(Payment.received_at), desc(Payment.id))
        .first()
    )

    if latest_real_payment is None:
        trader.spendable_balance = 0
        trader.total_contributed = 0
        return

    trader.spendable_balance = float(latest_real_payment.spendable_portion or 0)
    trader.total_contributed = float(latest_real_payment.amount_received or 0)


def clear_fake_demo_data(phone: str, keep_transaction_ref: str | None = None) -> None:
    db = SessionLocal()
    try:
        trader, identity = _resolve_demo_trader(db, phone)
        if not trader:
            print(f"No demo trader found for phone {phone}")
            return

        if trader.phone != phone:
            print(f"Resolved demo phone {phone} to linked trader {trader.phone}")

        if keep_transaction_ref:
            print(f"Cleaning demo trader {trader.phone}: keeping transaction ref {keep_transaction_ref}")
        else:
            print(f"Cleaning demo trader {trader.phone}: deleting seed/fake rows")

        deleted = _delete_older_rows(db, trader, identity, keep_transaction_ref)
        _recalculate_from_latest_non_fake_payment(db, trader)

        db.commit()

        print("Cleanup complete.")
        print(f"Spendable balance: {float(trader.spendable_balance):.2f}")
        print(f"Total contributed: {float(trader.total_contributed):.2f}")
        print(
            "Deleted rows: "
            f"payments={deleted['payments']}, "
            f"ledger_entries={deleted['ledger_entries']}, "
            f"pool_contributions={deleted['pool_contributions']}, "
            f"esusu_contributions={deleted['esusu_contributions']}, "
            f"esusu_rounds={deleted['esusu_rounds']}, "
            f"esusu_members={deleted['esusu_members']}, "
            f"esusu_cycles={deleted['esusu_cycles']}"
        )

    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Remove fake demo rows and rebuild the trader balance from the latest non-seed payment."
        )
    )
    parser.add_argument(
        "--phone",
        default=_default_demo_phone(),
        help="Trader phone number in canonical 0XXXXXXXXXX format.",
    )
    parser.add_argument(
        "--keep-transaction-ref",
        help="Keep this exact payment if it exists, instead of deleting every payment matching fake seed patterns.",
    )
    args = parser.parse_args()
    clear_fake_demo_data(phone=args.phone, keep_transaction_ref=args.keep_transaction_ref)


if __name__ == "__main__":
    main()