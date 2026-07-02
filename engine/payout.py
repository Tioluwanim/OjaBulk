"""
engine/payout.py

Pool payout trigger — fires when a pool reaches its target.

Critical ordering rule:
    Pool status MUST flip to FULFILLED as the very first DB write,
    before the Nomba Transfer call. This prevents the refund checker
    from ever seeing a mid-payout pool as still open.
"""

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session

from models.pool import Pool, PoolStatus
from models.pool_contribution import PoolContribution, ContributionStatus
from models.ledger_entry import LedgerEntry, EntryType
from services.transfers import transfer_service
from services.sms import sms_service


def trigger_payout(db: Session, pool: Pool) -> dict:
    """
    Executes supplier payout for a fulfilled pool.

    Args:
        db:   Database session
        pool: Pool ORM object that has reached its target

    Returns:
        {
            "pool_id":      str,
            "amount_paid":  float,
            "transfer_ref": str,
        }

    Raises:
        Exception if Nomba Transfer fails (caller handles retry logic)
    """

    # ── Step 1: Flip status to FULFILLED immediately ───────────────────────
    # This MUST happen first — prevents refund checker racing with this payout
    pool.status = PoolStatus.FULFILLED
    pool.fulfilled_at = datetime.now(timezone.utc)
    db.flush()   # Write to DB before making the transfer call

    # ── Step 2: Call Nomba Transfers API ──────────────────────────────────
    transfer_result = transfer_service.send_to_supplier(
        pool_id=str(pool.id),
        pool_title=pool.title,
        amount=pool.current_locked_amount,
        supplier_account_number=pool.supplier_account_number,
        supplier_bank_code=pool.supplier_bank_code,
        supplier_name=pool.supplier_name,
    )

    # ── Step 3: Release all locked contributions ───────────────────────────
    contributions = db.query(PoolContribution).filter(
        PoolContribution.pool_id == pool.id,
        PoolContribution.status == ContributionStatus.LOCKED,
    ).all()

    for contribution in contributions:
        contribution.status = ContributionStatus.RELEASED

        db.add(LedgerEntry(
            trader_id=contribution.trader_id,
            pool_id=pool.id,
            entry_type=EntryType.POOL_RELEASE_PAYOUT,
            amount=contribution.amount_locked,
            balance_after=contribution.trader.spendable_balance,
            note=(
                f"Pool fulfilled — \u20a6{contribution.amount_locked:,.0f} "
                f"released to supplier {pool.supplier_name}. "
                f"Pool: {pool.title}"
            ),
        ))

    db.commit()

    # ── Step 4: Notify all contributors ───────────────────────────────────
    for contribution in contributions:
        try:
            sms_service.send_pool_fulfilled(
                phone=contribution.trader.phone,
                trader_name=contribution.trader.name,
                pool_title=pool.title,
                contribution_amount=contribution.amount_locked,
                supplier_name=pool.supplier_name,
            )
        except Exception as e:
            # SMS failure must never crash the payout flow
            print(
                f"[Payout] SMS failed for trader {contribution.trader_id}: {e}"
            )

    return {
        "pool_id":      str(pool.id),
        "amount_paid":  pool.current_locked_amount,
        "transfer_ref": transfer_result.get("transfer_ref", ""),
    }