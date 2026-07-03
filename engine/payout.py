"""
engine/payout.py

Pool payout trigger.

Flow:

1. Mark pool fulfilled
2. Transfer funds from pool sub-account
3. Release locked contributions
4. Create ledger entries
5. Notify contributors
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models.pool import Pool, PoolStatus
from models.pool_contribution import (
    PoolContribution,
    ContributionStatus,
)
from models.ledger_entry import (
    LedgerEntry,
    EntryType,
)

from services.transfers import transfer_service
from services.sms import sms_service


def trigger_payout(
    db: Session,
    pool: Pool,
) -> dict:
    """
    Execute supplier payout.

    Returns:
    {
        "pool_id": str,
        "amount_paid": float,
        "transfer_ref": str,
    }
    """

    if not pool.sub_account_id:
        raise ValueError(
            f"Pool {pool.id} has no Nomba sub-account."
        )

    # --------------------------------------------------
    # Step 1
    # Mark fulfilled BEFORE transfer
    # --------------------------------------------------

    pool.status = PoolStatus.FULFILLED
    pool.fulfilled_at = datetime.now(
        timezone.utc
    )

    db.flush()

    # --------------------------------------------------
    # Step 2
    # Nomba transfer
    # --------------------------------------------------

    transfer_result = (
        transfer_service.send_to_supplier(
            sub_account_id=pool.sub_account_id,
            amount=float(
                pool.current_locked_amount
            ),
            supplier_account_number=(
                pool.supplier_account_number
            ),
            supplier_bank_code=(
                pool.supplier_bank_code
            ),
            supplier_name=(
                pool.supplier_name
            ),
            narration=(
                f"OjaBulk Pool "
                f"{pool.title}"
            ),
        )
    )

    transfer_ref = (
        transfer_result.get(
            "session_id"
        )
        or transfer_result.get(
            "transfer_ref"
        )
        or ""
    )

    # --------------------------------------------------
    # Step 3
    # Release contributions
    # --------------------------------------------------

    contributions = (
        db.query(
            PoolContribution
        )
        .filter(
            PoolContribution.pool_id
            == pool.id,
            PoolContribution.status
            == ContributionStatus.LOCKED,
        )
        .all()
    )

    for contribution in contributions:

        contribution.status = (
            ContributionStatus.RELEASED
        )

        db.add(
            LedgerEntry(
                trader_id=(
                    contribution.trader_id
                ),
                pool_id=pool.id,
                entry_type=(
                    EntryType.POOL_RELEASE_PAYOUT
                ),
                amount=(
                    contribution.amount_locked
                ),
                balance_after=(
                    contribution.trader.spendable_balance
                ),
                note=(
                    f"Pool fulfilled. "
                    f"₦{contribution.amount_locked:,.0f} "
                    f"released to supplier "
                    f"{pool.supplier_name}. "
                    f"Pool: {pool.title}"
                ),
            )
        )

    db.commit()

    # --------------------------------------------------
    # Step 4
    # Notify contributors
    # --------------------------------------------------

    for contribution in contributions:

        try:
            sms_service.send_pool_fulfilled(
                phone=(
                    contribution.trader.phone
                ),
                trader_name=(
                    contribution.trader.name
                ),
                pool_title=pool.title,
                contribution_amount=(
                    contribution.amount_locked
                ),
                supplier_name=(
                    pool.supplier_name
                ),
            )

        except Exception as e:

            print(
                "[Payout] SMS failed "
                f"for trader "
                f"{contribution.trader_id}: "
                f"{e}"
            )

    return {
        "pool_id": str(pool.id),
        "amount_paid": float(
            pool.current_locked_amount
        ),
        "transfer_ref": transfer_ref,
    }