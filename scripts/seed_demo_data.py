"""
scripts/seed_demo_data.py

Seeds realistic demo data for the OjaBulk hackathon demo.

Creates:
    - 12 traders across 3 Nigerian markets, with real-looking Nigerian
      names, phone numbers, stall numbers, and virtual account numbers
    - 3 pools in three different states, matching the demo script:
        1. "Rice Bulk Buy" — OPEN, ~64% funded, several days left
           (shows the happy-path progress bar mid-flight)
        2. "Palm Oil Bulk Buy" — FULFILLED, target hit, supplier paid
           (shows the automatic payout success state)
        3. "Beans Bulk Buy" — REFUNDED, deadline passed, funds returned
           (shows the automatic refund path — your judging differentiator)
    - Matching PoolContribution rows for every trader in every pool
    - A full, correct LedgerEntry audit trail for every single balance
      change, so the /traders/{id}/ledger endpoint has real history to
      display, and the reconciliation report has real numbers to check
    - Payment rows for every simulated inbound transfer, each with a
      unique nomba_transaction_ref (idempotency key), so re-running this
      script is safe — see IMPORTANT NOTE below

IMPORTANT — VIRTUAL ACCOUNT NUMBERS ARE FAKE:
    This script does NOT call the real Nomba API. The virtual account
    numbers assigned here (e.g. "9010000001") are fake placeholders for
    display purposes only — they will NOT receive real money. This is
    intentional: seeding demo data should never make real Nomba API
    calls (no cost, no rate limits, no risk of touching your real
    sandbox account). If you want a trader to receive REAL sandbox
    money during the live demo, register that ONE trader through the
    real POST /traders endpoint separately, so it goes through
    services/virtual_accounts.py and gets a real Nomba-issued account.

USAGE:
    python -m scripts.seed_demo_data
    (run from the project root, so imports resolve correctly)

SAFE TO RE-RUN:
    Running this script twice will raise an IntegrityError on the
    UNIQUE trader.phone constraint, by design — this stops you from
    accidentally doubling your demo data five minutes before presenting.
    If you need to reset and reseed, use the --reset flag:

    python -m scripts.seed_demo_data --reset
"""

import sys
import uuid
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from core.database import Base, engine, SessionLocal
import models
from models import (
    Trader,
    Pool,
    PoolStatus,
    PoolContribution,
    ContributionStatus,
    Payment,
    LedgerEntry,
    EntryType,
)


# ============================================================
# DEMO DATA DEFINITIONS
# ============================================================

TRADERS_DATA = [
    # (name, phone, stall_number, market_name, fake_va_number, fake_bank)
    ("Emeka Okafor",     "08011111001", "B-032", "Onitsha Main Market", "9010000001", "Wema Bank"),
    ("Chioma Eze",       "08011111002", "C-011", "Onitsha Main Market", "9010000002", "GTBank"),
    ("Tunde Bakare",     "08011111003", "D-005", "Alaba International Market", "9010000003", "Access Bank"),
    ("Amaka Nwosu",      "08011111004", "D-006", "Alaba International Market", "9010000004", "Zenith Bank"),
    ("Bola Ige",         "08011111005", "E-001", "Wuse Market", "9010000005", "UBA"),
    ("Folake Adewale",   "08011111006", "F-020", "Mile 12 Market", "9010000006", "First Bank"),
    ("Kunle Adebayo",    "08011111007", "G-010", "Aba Ariaria Market", "9010000007", "FCMB"),
    ("Ngozi Chukwu",     "08011111008", "B-014", "Onitsha Main Market", "9010000008", "Wema Bank"),
    ("Musa Ibrahim",     "08011111009", "H-003", "Kano Sabon Gari Market", "9010000009", "GTBank"),
    ("Grace Okonkwo",    "08011111010", "C-022", "Onitsha Main Market", "9010000010", "Access Bank"),
    ("Ahmed Suleiman",   "08011111011", "H-008", "Kano Sabon Gari Market", "9010000011", "Zenith Bank"),
    ("Blessing Uche",    "08011111012", "F-033", "Mile 12 Market", "9010000012", "UBA"),
]


def now_utc():
    return datetime.now(timezone.utc)


def make_ref(prefix: str) -> str:
    """Unique-enough fake transaction reference for seeded Payment rows."""
    return f"SEED-{prefix}-{uuid.uuid4().hex[:12]}"


# ============================================================
# SEEDING LOGIC
# ============================================================

def seed_traders(db) -> list[Trader]:
    """
    Creates all 12 traders with FAKE virtual account numbers.
    See module docstring — these do not receive real Nomba money.
    """
    traders = []
    for name, phone, stall, market, fake_va, fake_bank in TRADERS_DATA:
        trader = Trader(
            id=uuid.uuid4(),
            name=name,
            phone=phone,
            stall_number=stall,
            market_name=market,
            virtual_account_number=fake_va,
            bank_name=fake_bank,
            bank_account_name=f"OjaBulk-{name}",
            spendable_balance=Decimal("0"),
            total_contributed=Decimal("0"),
        )
        db.add(trader)
        traders.append(trader)

    db.flush()
    print(f"  Created {len(traders)} traders")
    return traders


def credit_spendable(db, trader: Trader, amount: Decimal, note: str, tx_ref: str):
    """
    Records a spendable credit exactly the way the real reconciliation
    engine does: update balance, write matching Payment + LedgerEntry
    rows. Keeps seeded data internally consistent with real webhook
    processing, so the reconciliation report and ledger views behave
    identically to production data.
    """
    trader.spendable_balance = trader.spendable_balance + amount
    trader.total_contributed = trader.total_contributed + amount

    db.add(Payment(
        id=uuid.uuid4(),
        trader_id=trader.id,
        amount_received=amount,
        nomba_transaction_ref=tx_ref,
        spendable_portion=amount,
        pool_portion=Decimal("0"),
        pool_id=None,
    ))
    db.add(LedgerEntry(
        id=uuid.uuid4(),
        trader_id=trader.id,
        pool_id=None,
        entry_type=EntryType.SPENDABLE_CREDIT,
        amount=amount,
        balance_after=trader.spendable_balance,
        note=note,
    ))


def lock_into_pool(db, trader: Trader, pool: Pool, amount: Decimal, note: str, tx_ref: str):
    """
    Records a pool contribution exactly the way the real reconciliation
    engine does: create/update PoolContribution, update pool total,
    write matching Payment + LedgerEntry rows.
    """
    contribution = PoolContribution(
        id=uuid.uuid4(),
        trader_id=trader.id,
        pool_id=pool.id,
        amount_locked=amount,
        status=ContributionStatus.LOCKED,
    )
    db.add(contribution)

    pool.current_locked_amount = pool.current_locked_amount + amount
    trader.total_contributed = trader.total_contributed + amount

    db.add(Payment(
        id=uuid.uuid4(),
        trader_id=trader.id,
        amount_received=amount,
        nomba_transaction_ref=tx_ref,
        spendable_portion=Decimal("0"),
        pool_portion=amount,
        pool_id=pool.id,
    ))
    db.add(LedgerEntry(
        id=uuid.uuid4(),
        trader_id=trader.id,
        pool_id=pool.id,
        entry_type=EntryType.POOL_LOCK,
        amount=amount,
        balance_after=trader.spendable_balance,
        note=note,
    ))
    return contribution


def seed_pool_1_open_in_progress(db, traders: list[Trader]) -> Pool:
    """
    Pool 1: Rice Bulk Buy — OPEN, ~64% funded, 9 days remaining.
    This is your "happy path mid-flight" demo screen — the progress
    bar that judges see first, showing the mechanism clearly without
    it being finished yet.
    """
    pool = Pool(
        id=uuid.uuid4(),
        title="Rice Bulk Buy — July 2026",
        description=(
            "Bulk purchase of 100 bags of 50kg parboiled rice from "
            "ABC Distributors at wholesale price. Target unlocks a "
            "15% discount versus buying individually from middlemen."
        ),
        target_amount=Decimal("500000.00"),
        current_locked_amount=Decimal("0"),
        fulfilled_amount=Decimal("0"),
        minimum_contributors=5,
        supplier_name="ABC Distributors Ltd",
        supplier_account_number="1234567890",
        supplier_bank_code="044",
        status=PoolStatus.OPEN,
        deadline=now_utc() + timedelta(days=9),
    )
    db.add(pool)
    db.flush()

    # 5 traders contribute varying amounts, totalling 320,000 of 500,000 (64%)
    contributions = [
        (traders[0], Decimal("80000.00")),   # Emeka
        (traders[1], Decimal("65000.00")),   # Chioma
        (traders[7], Decimal("55000.00")),   # Ngozi
        (traders[9], Decimal("70000.00")),   # Grace
        (traders[2], Decimal("50000.00")),   # Tunde
    ]
    for trader, amount in contributions:
        lock_into_pool(
            db, trader, pool, amount,
            note=f"Payment received — \u20a6{amount:,.0f} locked in {pool.title}",
            tx_ref=make_ref("RICE"),
        )

    print(f"  Pool 1 '{pool.title}': OPEN, "
          f"\u20a6{pool.current_locked_amount:,.0f} of \u20a6{pool.target_amount:,.0f} "
          f"({float(pool.current_locked_amount) / float(pool.target_amount) * 100:.0f}%)")
    return pool


def seed_pool_2_fulfilled(db, traders: list[Trader]) -> Pool:
    """
    Pool 2: Palm Oil Bulk Buy — FULFILLED, target hit, supplier paid.
    This is your "automatic payout succeeded" demo screen.
    """
    pool = Pool(
        id=uuid.uuid4(),
        title="Palm Oil Bulk Buy — June 2026",
        description=(
            "Bulk purchase of 50 drums of palm oil from Sunrise Palm "
            "Produce at wholesale rate."
        ),
        target_amount=Decimal("200000.00"),
        current_locked_amount=Decimal("0"),  # loop below builds this up to target
        fulfilled_amount=Decimal("0"),       # set to target AFTER the loop, below
        minimum_contributors=4,
        supplier_name="Sunrise Palm Produce",
        supplier_account_number="2233445566",
        supplier_bank_code="058",
        nomba_transfer_ref="SEED-TRANSFER-DEMO-PALM-OIL",
        status=PoolStatus.FULFILLED,
        deadline=now_utc() - timedelta(days=3),
        fulfilled_at=now_utc() - timedelta(days=3, hours=-2),
    )
    db.add(pool)
    db.flush()

    contributions = [
        (traders[3], Decimal("60000.00")),   # Amaka
        (traders[4], Decimal("55000.00")),   # Bola
        (traders[5], Decimal("45000.00")),   # Folake
        (traders[6], Decimal("40000.00")),   # Kunle
    ]
    for trader, amount in contributions:
        contribution = lock_into_pool(
            db, trader, pool, amount,
            note=f"Payment received — \u20a6{amount:,.0f} locked in {pool.title}",
            tx_ref=make_ref("PALM"),
        )
        # Immediately mark released + write the payout ledger entry,
        # exactly matching what engine/payout.py does on a real fulfillment
        contribution.status = ContributionStatus.RELEASED
        db.add(LedgerEntry(
            id=uuid.uuid4(),
            trader_id=trader.id,
            pool_id=pool.id,
            entry_type=EntryType.POOL_RELEASE_PAYOUT,
            amount=amount,
            balance_after=trader.spendable_balance,
            note=(
                f"Pool fulfilled — \u20a6{amount:,.0f} released to supplier "
                f"{pool.supplier_name}. Pool: {pool.title}"
            ),
        ))

    # Now that the loop has built current_locked_amount up to the real
    # total (200,000), mirror that into fulfilled_amount to reflect the
    # amount actually paid out — matching what engine/payout.py records
    # on a real fulfillment.
    pool.fulfilled_amount = pool.current_locked_amount

    print(f"  Pool 2 '{pool.title}': FULFILLED, "
          f"\u20a6{pool.current_locked_amount:,.0f} paid to {pool.supplier_name}")
    return pool


def seed_pool_3_refunded(db, traders: list[Trader]) -> Pool:
    """
    Pool 3: Beans Bulk Buy — REFUNDED, deadline missed, funds returned.
    This is your judging differentiator demo screen — the automatic
    refund path most other teams will not have built or demoed.
    """
    pool = Pool(
        id=uuid.uuid4(),
        title="Beans Bulk Buy — June 2026",
        description=(
            "Bulk purchase of 80 bags of brown beans from Northern "
            "Grains Co-operative. Did not reach target before deadline."
        ),
        target_amount=Decimal("300000.00"),
        current_locked_amount=Decimal("0"),  # zeroed out after refund
        fulfilled_amount=Decimal("0"),
        minimum_contributors=6,
        supplier_name="Northern Grains Co-operative",
        supplier_account_number="3344556677",
        supplier_bank_code="011",
        status=PoolStatus.REFUNDED,
        deadline=now_utc() - timedelta(days=5),
        refunded_at=now_utc() - timedelta(days=5, hours=-1),
    )
    db.add(pool)
    db.flush()

    # Two traders contributed, fell short of target, then got refunded
    contributions = [
        (traders[8], Decimal("15000.00")),   # Musa
        (traders[10], Decimal("8000.00")),   # Ahmed
    ]
    for trader, amount in contributions:
        # Record the original lock, exactly as it happened before expiry
        contribution = PoolContribution(
            id=uuid.uuid4(),
            trader_id=trader.id,
            pool_id=pool.id,
            amount_locked=amount,
            status=ContributionStatus.REFUNDED,  # final state, post-refund
        )
        db.add(contribution)

        lock_ref = make_ref("BEANS-LOCK")
        db.add(Payment(
            id=uuid.uuid4(),
            trader_id=trader.id,
            amount_received=amount,
            nomba_transaction_ref=lock_ref,
            spendable_portion=Decimal("0"),
            pool_portion=amount,
            pool_id=pool.id,
        ))
        db.add(LedgerEntry(
            id=uuid.uuid4(),
            trader_id=trader.id,
            pool_id=pool.id,
            entry_type=EntryType.POOL_LOCK,
            amount=amount,
            balance_after=trader.spendable_balance,
            note=f"Payment received — \u20a6{amount:,.0f} locked in {pool.title}",
        ))

        # Now the refund itself: money returns to spendable, exactly
        # matching what engine/refund.py does on a real deadline miss
        trader.spendable_balance = trader.spendable_balance + amount
        db.add(LedgerEntry(
            id=uuid.uuid4(),
            trader_id=trader.id,
            pool_id=pool.id,
            entry_type=EntryType.POOL_REFUND,
            amount=amount,
            balance_after=trader.spendable_balance,
            note=(
                f"Pool deadline missed — \u20a6{amount:,.0f} refunded from "
                f"{pool.title} to spendable balance"
            ),
        ))

    print(f"  Pool 3 '{pool.title}': REFUNDED, "
          f"2 contributors refunded to spendable balance")
    return pool


def seed_extra_spendable_balances(db, traders: list[Trader]):
    """
    Gives a few traders extra spendable balance not tied to any pool —
    simulates overpayment scenarios and traders who haven't joined a
    pool yet but have sent money. Makes the trader list and ledger
    views look realistic rather than every trader having a suspiciously
    round, pool-only balance.
    """
    extras = [
        (traders[11], Decimal("12500.00")),  # Blessing — no pool yet
        (traders[0],  Decimal("2500.00")),   # Emeka — overpayment excess
        (traders[4],  Decimal("5000.00")),   # Bola — extra after pool fulfilled
    ]
    for trader, amount in extras:
        credit_spendable(
            db, trader, amount,
            note=f"Payment received — \u20a6{amount:,.0f} added to spendable balance",
            tx_ref=make_ref("EXTRA"),
        )
    print(f"  Added extra spendable balances for {len(extras)} traders")


# ============================================================
# RESET LOGIC
# ============================================================

def reset_all_data(db):
    """
    Deletes all seeded data in FK-safe order. Only affects the tables
    this script touches — does not drop or recreate tables.
    """
    print("Resetting existing data...")
    db.query(LedgerEntry).delete()
    db.query(Payment).delete()
    db.query(PoolContribution).delete()
    db.query(Pool).delete()
    db.query(Trader).delete()
    db.commit()
    print("  All existing demo data cleared\n")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Seed OjaBulk demo data")
    parser.add_argument(
        "--reset", action="store_true",
        help="Delete all existing Trader/Pool/Payment/LedgerEntry rows first"
    )
    args = parser.parse_args()

    print("OjaBulk demo data seeder")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if args.reset:
            reset_all_data(db)

        existing = db.query(Trader).count()
        if existing > 0 and not args.reset:
            print(
                f"ERROR: {existing} trader(s) already exist in the database.\n"
                f"Re-running this script without --reset would create "
                f"duplicate phone numbers and fail on the UNIQUE constraint.\n\n"
                f"To wipe and reseed, run:\n"
                f"    python -m scripts.seed_demo_data --reset\n"
            )
            sys.exit(1)

        print("\nSeeding traders...")
        traders = seed_traders(db)

        print("\nSeeding pools...")
        pool1 = seed_pool_1_open_in_progress(db, traders)
        pool2 = seed_pool_2_fulfilled(db, traders)
        pool3 = seed_pool_3_refunded(db, traders)

        print("\nSeeding extra spendable balances...")
        seed_extra_spendable_balances(db, traders)

        db.commit()

        print("\n" + "=" * 60)
        print("SEED COMPLETE")
        print("=" * 60)
        print(f"  Traders: {len(traders)}")
        print(f"  Pools:   3 (1 open, 1 fulfilled, 1 refunded)")
        print(f"  Markets: Onthisa Main, Alaba International, Wuse, "
              f"Mile 12, Aba Ariaria, Kano Sabon Gari")
        print()
        print("  Reminder: all virtual account numbers seeded here are FAKE")
        print("  placeholders for display only. For a live demo payment,")
        print("  register one additional trader through the real")
        print("  POST /traders endpoint to get a real Nomba sandbox account.")

    except Exception as e:
        db.rollback()
        print(f"\nSeed failed, rolled back: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
