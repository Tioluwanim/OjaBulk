"""
engine/refund.py

Pool refund trigger — fires when a pool misses its deadline.

Called by:
    background/pool_expiry_checker.py (scheduled job)
    GET /pools/{id} route (on-demand check when pool detail is viewed)
    POST /pools/{id}/check-expiry (manual trigger for demo)
"""

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session

from models.pool import Pool, PoolStatus
from models.pool_contribution import PoolContribution, ContributionStatus
from models.trader import Trader
from models.ledger_entry import LedgerEntry, EntryType
from services.sms import sms_service


def refund_pool(db: Session, pool: Pool) -> dict:
    """
    Refunds all contributors when a pool misses its deadline.

    Args:
        db:   Database session
        pool: Pool ORM object past its deadline without hitting target

    Returns:
        {
            "pool_id":             str,
            "total_refunded":      float,
            "contributors_count":  int,
        }
    """
    # ── Step 1: Flip status to REFUNDED immediately ────────────────────────
    pool.status = PoolStatus.REFUNDED
    pool.refunded_at = datetime.now(timezone.utc)
    db.flush()

    # ── Step 2: Return every locked contribution to spendable balance ──────
    contributions = db.query(PoolContribution).filter(
        PoolContribution.pool_id == pool.id,
        PoolContribution.status == ContributionStatus.LOCKED,
    ).all()

    total_refunded = Decimal("0")

    for contribution in contributions:
        refund_amount = Decimal(str(contribution.amount_locked))
        total_refunded += refund_amount

        trader = db.query(Trader).filter(
            Trader.id == contribution.trader_id
        ).first()

        if not trader:
            continue

        # Return to spendable
        trader.spendable_balance = float(
            Decimal(str(trader.spendable_balance)) + refund_amount
        )
        contribution.status = ContributionStatus.REFUNDED

        db.add(LedgerEntry(
            trader_id=trader.id,
            pool_id=pool.id,
            entry_type=EntryType.POOL_REFUND,
            amount=float(refund_amount),
            balance_after=trader.spendable_balance,
            note=(
                f"Pool deadline missed — \u20a6{refund_amount:,.0f} "
                f"refunded from {pool.title} to spendable balance"
            ),
        ))

    db.commit()

    # ── Step 3: Notify all contributors ───────────────────────────────────
    for contribution in contributions:
        try:
            trader = db.query(Trader).filter(
                Trader.id == contribution.trader_id
            ).first()
            if trader:
                sms_service.send_pool_refunded(
                    phone=trader.phone,
                    trader_name=trader.name,
                    pool_title=pool.title,
                    refund_amount=contribution.amount_locked,
                )
        except Exception as e:
            print(
                f"[Refund] SMS failed for trader {contribution.trader_id}: {e}"
            )

    return {
        "pool_id":            str(pool.id),
        "total_refunded":     float(total_refunded),
        "contributors_count": len(contributions),
    }


def check_and_refund_expired_pools(db: Session) -> list[dict]:
    """
    Finds all open pools past their deadline and refunds them.
    Called by the background job.

    Returns:
        List of refund result dicts, one per expired pool processed
    """
    now = datetime.now(timezone.utc)

    expired_pools = db.query(Pool).filter(
        Pool.status == PoolStatus.OPEN,
        Pool.deadline < now,
    ).all()

    results = []
    for pool in expired_pools:
        try:
            result = refund_pool(db=db, pool=pool)
            results.append(result)
            print(
                f"[Refund] Pool {pool.id} ({pool.title}) refunded. "
                f"Total: \u20a6{result['total_refunded']:,.0f} "
                f"to {result['contributors_count']} traders."
            )
        except Exception as e:
            print(f"[Refund] Failed to refund pool {pool.id}: {e}")

    return results
