"""
engine/reconciliation.py

The core OjaBulk reconciliation engine.

This is the most important file in the entire project.
It takes one raw fact (money arrived at a virtual account)
and resolves it into a fully specified, internally consistent
set of database state changes.

Flow:
    1. Idempotency check (already processed this ref?)
    2. Identity resolution (which trader owns this account?)
    3. Active pool lookup (which pool is this trader targeting?)
    4. Allocation split (how much goes to pool vs spendable?)
    5. Database writes (ledger entries + balance updates)
    6. Payout trigger check (did the pool just hit its target?)
    7. SMS notification
"""

from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models.trader import Trader
from models.pool import Pool, PoolStatus
from models.pool_contribution import PoolContribution, ContributionStatus
from models.payment import Payment
from models.ledger_entry import LedgerEntry, EntryType
from services.sms import sms_service
from engine.payout import trigger_payout


class PaymentAlreadyProcessedError(Exception):
    """Raised when a transaction ref has already been processed."""
    pass


class TraderNotFoundError(Exception):
    """Raised when no trader matches the incoming virtual account number."""
    pass


def reconcile(
    db: Session,
    virtual_account_number: str,
    amount_received: float,
    transaction_ref: str,
) -> dict:
    """
    Main reconciliation function. Called by the webhook route handler
    inside a background task after HMAC verification passes.

    Args:
        db:                     SQLAlchemy database session
        virtual_account_number: The virtual account that received money
        amount_received:        Amount in naira (not kobo)
        transaction_ref:        Nomba's unique transaction reference (idempotency key)

    Returns:
        {
            "trader_id":      str,
            "pool_cut":       float,
            "spendable_cut":  float,
            "pool_id":        str | None,
            "pool_fulfilled": bool,
        }

    Raises:
        PaymentAlreadyProcessedError: If this ref was already processed
        TraderNotFoundError:          If no trader owns this virtual account
    """
    amount = Decimal(str(amount_received))

    # ── Step 1: Idempotency check ──────────────────────────────────────────
    existing_payment = db.query(Payment).filter(
        Payment.nomba_transaction_ref == transaction_ref
    ).first()

    if existing_payment:
        raise PaymentAlreadyProcessedError(
            f"Transaction {transaction_ref} already processed. "
            f"Ignoring duplicate webhook delivery."
        )

    # ── Step 2: Identity resolution ────────────────────────────────────────
    trader = db.query(Trader).filter(
        Trader.virtual_account_number == virtual_account_number
    ).first()

    if not trader:
        raise TraderNotFoundError(
            f"No trader found for virtual account {virtual_account_number}. "
            f"Storing in manual review queue."
        )

    # ── Step 3: Active pool lookup ─────────────────────────────────────────
    active_contribution = db.query(PoolContribution).filter(
        PoolContribution.trader_id == trader.id,
        PoolContribution.status == ContributionStatus.LOCKED,
    ).join(Pool).filter(
        Pool.status == PoolStatus.OPEN
    ).first()

    active_pool = active_contribution.pool if active_contribution else None

    # ── Step 4: Allocation split ───────────────────────────────────────────
    pool_cut = Decimal("0")
    spendable_cut = Decimal("0")
    pool_id = None

    if active_pool:
        remaining_gap = (
            Decimal(str(active_pool.target_amount))
            - Decimal(str(active_pool.current_locked_amount))
        )
        # Lock only up to the remaining gap — excess goes to spendable
        pool_cut = min(amount, remaining_gap)
        spendable_cut = amount - pool_cut
        pool_id = active_pool.id
    else:
        # No active pool — everything goes to spendable
        spendable_cut = amount

    # ── Step 5: Database writes ────────────────────────────────────────────
    # All writes happen together — if any fail, all roll back

    # 5a. Pool contribution update
    if pool_cut > 0 and active_pool:
        if active_contribution:
            active_contribution.amount_locked = float(
                Decimal(str(active_contribution.amount_locked)) + pool_cut
            )
        else:
            new_contribution = PoolContribution(
                trader_id=trader.id,
                pool_id=active_pool.id,
                amount_locked=float(pool_cut),
                status=ContributionStatus.LOCKED,
            )
            db.add(new_contribution)

        active_pool.current_locked_amount = float(
            Decimal(str(active_pool.current_locked_amount)) + pool_cut
        )

        db.add(LedgerEntry(
            trader_id=trader.id,
            pool_id=active_pool.id,
            entry_type=EntryType.POOL_LOCK,
            amount=float(pool_cut),
            balance_after=float(
                Decimal(str(trader.spendable_balance)) + spendable_cut
            ),
            note=(
                f"Payment \u20a6{amount:,.0f} received — "
                f"\u20a6{pool_cut:,.0f} locked in {active_pool.title}"
            ),
        ))

    # 5b. Spendable balance update
    if spendable_cut > 0:
        trader.spendable_balance = float(
            Decimal(str(trader.spendable_balance)) + spendable_cut
        )

        db.add(LedgerEntry(
            trader_id=trader.id,
            pool_id=None,
            entry_type=EntryType.SPENDABLE_CREDIT,
            amount=float(spendable_cut),
            balance_after=trader.spendable_balance,
            note=(
                f"Payment \u20a6{amount:,.0f} received — "
                f"\u20a6{spendable_cut:,.0f} added to spendable balance"
            ),
        ))

    # 5c. Total contributed tracking
    trader.total_contributed = float(
        Decimal(str(trader.total_contributed)) + amount
    )

    # 5d. Payment record (completes the idempotency guarantee)
    payment = Payment(
        trader_id=trader.id,
        amount_received=float(amount),
        nomba_transaction_ref=transaction_ref,
        spendable_portion=float(spendable_cut),
        pool_portion=float(pool_cut),
        pool_id=pool_id,
    )
    db.add(payment)
    db.flush()   # Flush to catch unique constraint violations early
    db.commit()

    # ── Step 6: Payout trigger check ──────────────────────────────────────
    pool_fulfilled = False
    if active_pool and active_pool.current_locked_amount >= active_pool.target_amount:
        try:
            trigger_payout(db=db, pool=active_pool)
            pool_fulfilled = True
        except Exception as e:
            # Payout failure must not roll back the payment record
            print(f"[Reconciliation] Payout trigger failed for pool {active_pool.id}: {e}")

    # ── Step 7: SMS notification ───────────────────────────────────────────
    pool_progress_pct = None
    if active_pool and active_pool.target_amount > 0:
        pool_progress_pct = (
            active_pool.current_locked_amount / active_pool.target_amount
        ) * 100

    sms_service.send_payment_received(
        phone=trader.phone,
        trader_name=trader.name,
        total_amount=float(amount),
        pool_cut=float(pool_cut),
        spendable_cut=float(spendable_cut),
        pool_name=active_pool.title if active_pool else None,
        pool_progress_pct=pool_progress_pct,
    )

    return {
        "trader_id":      str(trader.id),
        "pool_cut":       float(pool_cut),
        "spendable_cut":  float(spendable_cut),
        "pool_id":        str(pool_id) if pool_id else None,
        "pool_fulfilled": pool_fulfilled,
    }