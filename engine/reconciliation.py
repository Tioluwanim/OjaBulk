"""
engine/reconciliation.py

Core OjaBulk reconciliation engine.

Flow:
    1. Idempotency protection
    2. Trader resolution
    3. Active pool lookup
    4. Allocation split
    5. Database updates
    6. Pool payout trigger
    7. SMS notification
"""

from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.trader import Trader
from models.pool import Pool, PoolStatus
from models.pool_contribution import (
    PoolContribution,
    ContributionStatus,
)
from models.payment import Payment
from models.ledger_entry import (
    LedgerEntry,
    EntryType,
)

from services.sms import sms_service
from engine.payout import trigger_payout


class PaymentAlreadyProcessedError(Exception):
    """Duplicate webhook/payment."""
    pass


class TraderNotFoundError(Exception):
    """Virtual account not linked to a trader."""
    pass


def reconcile(
    db: Session,
    virtual_account_number: str,
    amount_received: float,
    transaction_ref: str,
) -> dict:
    """
    Reconcile one inbound payment from Nomba.
    """

    amount = Decimal(str(amount_received))

    # --------------------------------------------------
    # Step 1 — Idempotency protection
    # --------------------------------------------------

    existing_payment = (
        db.query(Payment)
        .filter(
            Payment.nomba_transaction_ref
            == transaction_ref
        )
        .first()
    )

    if existing_payment:
        raise PaymentAlreadyProcessedError(
            f"Transaction {transaction_ref} "
            f"already processed"
        )

    # --------------------------------------------------
    # Step 2 — Trader lookup
    # --------------------------------------------------

    trader = (
        db.query(Trader)
        .filter(
            Trader.virtual_account_number
            == virtual_account_number
        )
        .first()
    )

    if not trader:
        raise TraderNotFoundError(
            f"No trader found for virtual account "
            f"{virtual_account_number}"
        )

    # --------------------------------------------------
    # Step 3 — Find active pool
    # --------------------------------------------------

    active_contribution = (
        db.query(PoolContribution)
        .join(Pool)
        .filter(
            PoolContribution.trader_id == trader.id,
            PoolContribution.status == ContributionStatus.LOCKED,
            Pool.status == PoolStatus.OPEN,
        )
        .with_for_update()
        .first()
    )

    active_pool = (
        active_contribution.pool
        if active_contribution
        else None
    )

    # --------------------------------------------------
    # Step 4 — Allocation split
    # --------------------------------------------------

    pool_cut = Decimal("0")
    spendable_cut = Decimal("0")
    pool_id = None

    if active_pool:

        db.refresh(active_pool)

        remaining_gap = max(
            Decimal("0"),
            Decimal(str(active_pool.target_amount))
            - Decimal(
                str(
                    active_pool.current_locked_amount
                )
            ),
        )

        pool_cut = min(
            amount,
            remaining_gap,
        )

        spendable_cut = amount - pool_cut

        pool_id = active_pool.id

    else:
        spendable_cut = amount

    current_spendable = Decimal(
        str(trader.spendable_balance)
    )

    new_spendable_balance = (
        current_spendable
        + spendable_cut
    )

    try:

        # ------------------------------------------
        # Pool contribution updates
        # ------------------------------------------

        if pool_cut > 0 and active_pool:

            if active_contribution:

                active_contribution.amount_locked = float(
                    Decimal(
                        str(
                            active_contribution.amount_locked
                        )
                    )
                    + pool_cut
                )

            else:

                db.add(
                    PoolContribution(
                        trader_id=trader.id,
                        pool_id=active_pool.id,
                        amount_locked=float(
                            pool_cut
                        ),
                        status=ContributionStatus.LOCKED,
                    )
                )

            active_pool.current_locked_amount = float(
                Decimal(
                    str(
                        active_pool.current_locked_amount
                    )
                )
                + pool_cut
            )

            db.add(
                LedgerEntry(
                    trader_id=trader.id,
                    pool_id=active_pool.id,
                    entry_type=EntryType.POOL_LOCK,
                    amount=float(pool_cut),
                    balance_after=float(
                        new_spendable_balance
                    ),
                    note=(
                        f"Payment ₦{amount:,.2f} received — "
                        f"₦{pool_cut:,.2f} locked in "
                        f"{active_pool.title}"
                    ),
                )
            )

        # ------------------------------------------
        # Spendable balance
        # ------------------------------------------

        if spendable_cut > 0:

            trader.spendable_balance = float(
                new_spendable_balance
            )

            db.add(
                LedgerEntry(
                    trader_id=trader.id,
                    pool_id=None,
                    entry_type=EntryType.SPENDABLE_CREDIT,
                    amount=float(
                        spendable_cut
                    ),
                    balance_after=float(
                        new_spendable_balance
                    ),
                    note=(
                        f"Payment ₦{amount:,.2f} received — "
                        f"₦{spendable_cut:,.2f} added "
                        f"to spendable balance"
                    ),
                )
            )

        # ------------------------------------------
        # Lifetime contribution tracking
        # ------------------------------------------

        trader.total_contributed = float(
            Decimal(
                str(
                    trader.total_contributed
                )
            )
            + amount
        )

        # ------------------------------------------
        # Payment record
        # ------------------------------------------

        payment = Payment(
            trader_id=trader.id,
            amount_received=float(amount),
            nomba_transaction_ref=transaction_ref,
            spendable_portion=float(
                spendable_cut
            ),
            pool_portion=float(
                pool_cut
            ),
            pool_id=pool_id,
        )

        db.add(payment)

        db.flush()

        db.commit()

    except IntegrityError:

        db.rollback()

        raise PaymentAlreadyProcessedError(
            f"Transaction {transaction_ref} "
            f"already processed"
        )

    except Exception:

        db.rollback()
        raise

    # --------------------------------------------------
    # Refresh ORM objects
    # --------------------------------------------------

    if active_pool:
        db.refresh(active_pool)

    db.refresh(trader)

    # --------------------------------------------------
    # Step 5 — Payout trigger
    # --------------------------------------------------

    pool_fulfilled = False

    if (
        active_pool
        and active_pool.status == PoolStatus.OPEN
    ):

        current_locked = Decimal(
            str(
                active_pool.current_locked_amount
            )
        )

        target_amount = Decimal(
            str(
                active_pool.target_amount
            )
        )

        if current_locked >= target_amount:

            try:

                trigger_payout(
                    db=db,
                    pool=active_pool,
                )

                pool_fulfilled = True
                active_pool = db.query(Pool).filter(
                    Pool.id == active_pool.id
                ).first()

            except Exception as e:

                print(
                    "[Reconciliation] "
                    f"Payout failed for pool "
                    f"{active_pool.id}: {e}"
                )

    # --------------------------------------------------
    # Step 6 — SMS notification
    # --------------------------------------------------

    try:

        pool_progress_pct = None

        if (
            active_pool
            and Decimal(
                str(
                    active_pool.target_amount
                )
            )
            > Decimal("0")
        ):

            pool_progress_pct = round(
                (
                    Decimal(
                        str(
                            active_pool.current_locked_amount
                        )
                    )
                    / Decimal(
                        str(
                            active_pool.target_amount
                        )
                    )
                )
                * Decimal("100"),
                2,
            )

        sms_service.send_payment_received(
            phone=trader.phone,
            trader_name=trader.name,
            total_amount=float(amount),
            pool_cut=float(pool_cut),
            spendable_cut=float(
                spendable_cut
            ),
            pool_name=(
                active_pool.title
                if active_pool
                else None
            ),
            pool_progress_pct=(
                float(pool_progress_pct)
                if pool_progress_pct
                else None
            ),
        )

    except Exception as e:

        print(
            f"[SMS] Failed for trader "
            f"{trader.id}: {e}"
        )

    # --------------------------------------------------
    # Step 7 — Response
    # --------------------------------------------------

    return {
        "trader_id": str(trader.id),
        "pool_cut": float(pool_cut),
        "spendable_cut": float(
            spendable_cut
        ),
        "pool_id": (
            str(pool_id)
            if pool_id
            else None
        ),
        "pool_fulfilled": pool_fulfilled,
        "transaction_ref": transaction_ref,
    }