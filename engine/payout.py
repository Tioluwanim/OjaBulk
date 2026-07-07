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

    CORRECTED: removed the pool.sub_account_id check and the
    sub_account_id/narration kwargs passed to send_to_supplier().

    There is ONE sub-account for the whole business (NOMBA_SUB_ACCOUNT_ID
    in .env, read by services/client.py), not a separate sub-account per
    pool. Every trader's virtual account — and therefore every pool's
    pooled funds — lives inside that single shared sub-account. The
    transfer service itself (services/transfers.py) already scopes the
    outbound transfer URL to nomba_client.subaccount_id internally, so
    this function does not need to know or pass a sub-account id at all.

    FIX (pending-transfer handling):
    Nomba's transfer endpoint can return 201/"PROCESSING" — the transfer
    was accepted for processing but has not actually settled yet
    (transfer_service.send_to_supplier sets is_pending=True in that
    case). Previously this function treated 201 exactly like a
    confirmed 200 success: it released every contribution immediately
    and told contributors the payout was "confirmed", even though
    Nomba might still fail or reverse the transfer afterward. Now:
      - contributions stay LOCKED and the pool is marked
        PAYOUT_PROCESSING (not FULFILLED) whenever is_pending is True
      - contributors get a "payout initiated" SMS, not a "confirmed"
        SMS
      - background/payout_finalizer.py requeries Nomba periodically
        and only THEN releases contributions / marks the pool
        FULFILLED / sends the confirmation SMS, via
        finalize_pending_payout() below.

    Returns:
    {
        "pool_id": str,
        "amount_paid": float,
        "transfer_ref": str,
        "is_pending": bool,
    }
    """

    # --------------------------------------------------
    # Step 1
    # Nomba transfer -- scoped internally to the single
    # shared sub-account by transfer_service itself.
    # Done BEFORE flipping pool status, since we don't yet
    # know if this will be a confirmed or a pending result.
    # --------------------------------------------------

    transfer_result = (
        transfer_service.send_to_supplier(
            pool_id=str(pool.id),
            pool_title=pool.title,
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

    is_pending = bool(transfer_result.get("is_pending"))

    pool.nomba_transfer_ref = transfer_ref or None
    pool.fulfilled_amount = float(pool.current_locked_amount)

    if is_pending:
        # Transfer only ACCEPTED, not yet confirmed. Do NOT release
        # contributions or tell contributors the payout is done.
        pool.status = PoolStatus.PAYOUT_PROCESSING
        db.commit()

        contributions = (
            db.query(PoolContribution)
            .filter(
                PoolContribution.pool_id == pool.id,
                PoolContribution.status == ContributionStatus.LOCKED,
            )
            .all()
        )

        for contribution in contributions:
            try:
                sms_service.send_pool_payout_processing(
                    phone=contribution.trader.phone,
                    trader_name=contribution.trader.name,
                    pool_title=pool.title,
                    supplier_name=pool.supplier_name,
                )
            except Exception as e:
                print(
                    "[Payout] Processing SMS failed "
                    f"for trader {contribution.trader_id}: {e}"
                )

        return {
            "pool_id": str(pool.id),
            "amount_paid": float(pool.current_locked_amount),
            "transfer_ref": transfer_ref,
            "is_pending": True,
        }

    # --------------------------------------------------
    # Step 2 — Transfer confirmed synchronously. Finalize now.
    # --------------------------------------------------

    pool.status = PoolStatus.FULFILLED
    pool.fulfilled_at = datetime.now(timezone.utc)

    db.flush()

    _release_contributions_and_notify(db, pool)

    db.commit()

    return {
        "pool_id": str(pool.id),
        "amount_paid": float(
            pool.current_locked_amount
        ),
        "transfer_ref": transfer_ref,
        "is_pending": False,
    }


def _release_contributions_and_notify(db: Session, pool: Pool) -> None:
    """
    Shared by the synchronous-confirmation path above and by
    finalize_pending_payout() below — releases every LOCKED
    contribution for this pool, writes the ledger entries, and sends
    the "payout confirmed" SMS. Caller is responsible for committing.
    """
    contributions = (
        db.query(PoolContribution)
        .filter(
            PoolContribution.pool_id == pool.id,
            PoolContribution.status == ContributionStatus.LOCKED,
        )
        .all()
    )

    for contribution in contributions:

        contribution.status = ContributionStatus.RELEASED

        db.add(
            LedgerEntry(
                trader_id=contribution.trader_id,
                pool_id=pool.id,
                entry_type=EntryType.POOL_RELEASE_PAYOUT,
                amount=contribution.amount_locked,
                balance_after=contribution.trader.spendable_balance,
                note=(
                    f"Pool fulfilled. "
                    f"₦{contribution.amount_locked:,.0f} "
                    f"released to supplier "
                    f"{pool.supplier_name}. "
                    f"Pool: {pool.title}"
                ),
            )
        )

    db.flush()

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
            print(
                "[Payout] SMS failed "
                f"for trader {contribution.trader_id}: {e}"
            )


def finalize_pending_payout(db: Session, pool: Pool) -> dict:
    """
    Called by background/payout_finalizer.py for any pool sitting in
    PAYOUT_PROCESSING. Requeries Nomba for the real, current status of
    the transfer and only then either:
      - finalizes it (releases contributions, marks FULFILLED, sends
        the confirmation SMS), or
      - leaves it in PAYOUT_PROCESSING to be checked again next run
        if Nomba still reports it as processing, or
      - flags it for manual review if Nomba reports a hard failure,
        since silently leaving contributors' money in limbo is worse
        than a visible, loggable alert an admin can act on.
    """
    if not pool.nomba_transfer_ref:
        print(f"[PayoutFinalizer] Pool {pool.id} has no transfer_ref to requery — skipping.")
        return {"pool_id": str(pool.id), "action": "skipped_no_ref"}

    try:
        result = transfer_service.requery_transfer(pool.nomba_transfer_ref)
    except Exception as e:
        print(f"[PayoutFinalizer] Requery failed for pool {pool.id}: {e}")
        return {"pool_id": str(pool.id), "action": "requery_failed"}

    status = str(result.get("status", "")).upper()

    # Nomba's transaction-status values seen for transfers in
    # practice: SUCCESS/COMPLETED for confirmed, FAILED for a hard
    # failure, and PENDING/PROCESSING while still in flight.
    if status in ("SUCCESS", "SUCCESSFUL", "COMPLETED"):
        pool.status = PoolStatus.FULFILLED
        pool.fulfilled_at = datetime.now(timezone.utc)
        db.flush()
        _release_contributions_and_notify(db, pool)
        db.commit()
        print(f"[PayoutFinalizer] Pool {pool.id} confirmed and finalized.")
        return {"pool_id": str(pool.id), "action": "finalized"}

    if status in ("FAILED", "REVERSED", "DECLINED"):
        # Do NOT release contributions — the money never actually left
        # for the supplier. Flag loudly for manual review rather than
        # guessing at an automatic remediation (retry vs refund) here.
        print(
            f"[PayoutFinalizer] ALERT: transfer for pool {pool.id} "
            f"({pool.title}) came back '{status}'. Contributions remain "
            f"LOCKED. Manual review required — do not treat as paid."
        )
        return {"pool_id": str(pool.id), "action": "failed_needs_review", "status": status}

    # Still pending/processing — check again next run.
    print(f"[PayoutFinalizer] Pool {pool.id} still '{status}' — will recheck.")
    return {"pool_id": str(pool.id), "action": "still_pending", "status": status}