"""
background/payout_finalizer.py

Periodic background job — requeries Nomba for any pool whose payout
transfer was accepted (201/PROCESSING) but not yet confirmed, and
finalizes it (releases contributions, marks FULFILLED, sends the
confirmation SMS) once Nomba reports a final status.

Why this exists:
engine/payout.py's trigger_payout() used to treat a 201/"PROCESSING"
transfer response exactly like a confirmed success — releasing every
contributor's locked funds and sending a "payment sent, confirmed" SMS
immediately, even though Nomba had only accepted the transfer for
processing, not actually settled it. If that transfer later failed or
reversed, contributors would have already been told (falsely) that
their money reached the supplier.

Now, any pool left in PoolStatus.PAYOUT_PROCESSING by trigger_payout
sits here until this job confirms (or flags) the real outcome.
"""

from datetime import datetime, timezone
from apscheduler.triggers.interval import IntervalTrigger

from core.database import SessionLocal
from models.pool import Pool, PoolStatus
from engine.payout import finalize_pending_payout, trigger_payout


async def run_payout_finalizer():
    """
    Two things run here every 5 minutes:

    1. Requery every pool in PAYOUT_PROCESSING (Nomba accepted the
       transfer but hadn't confirmed it yet) and finalize once
       confirmed — the original purpose of this job.

    2. Retry every pool still OPEN whose current_locked_amount has
       already reached target_amount. This closes a real gap: if
       trigger_payout()'s call to Nomba's Transfer API raises before
       completing (network error, expired/invalid credentials, a
       transient 401/500, etc.), the pool's locked amount was already
       committed by the caller (reconciliation or
       contribute-from-spendable) BEFORE trigger_payout was invoked —
       so the pool is left fully funded but stuck at OPEN, with no
       automatic retry, since nothing else scans for "OPEN pools that
       already hit target." Without this, a transient Nomba failure
       permanently strands a fully-funded pool.
    """
    print(f"[PayoutFinalizer] Running at {datetime.now(timezone.utc).isoformat()}")
    db = SessionLocal()
    try:
        pending_pools = (
            db.query(Pool)
            .filter(Pool.status == PoolStatus.PAYOUT_PROCESSING)
            .all()
        )

        if not pending_pools:
            print("[PayoutFinalizer] No pools pending payout confirmation")
        else:
            for pool in pending_pools:
                try:
                    finalize_pending_payout(db, pool)
                except Exception as e:
                    print(f"[PayoutFinalizer] Error finalizing pool {pool.id}: {e}")

        stuck_pools = (
            db.query(Pool)
            .filter(Pool.status == PoolStatus.OPEN)
            .all()
        )
        stuck_pools = [
            p for p in stuck_pools
            if float(p.current_locked_amount) >= float(p.target_amount) and float(p.target_amount) > 0
        ]

        if not stuck_pools:
            print("[PayoutFinalizer] No fully-funded pools stuck at OPEN")
        else:
            for pool in stuck_pools:
                print(
                    f"[PayoutFinalizer] Pool {pool.id} ({pool.title}) is fully "
                    f"funded but still OPEN — retrying payout."
                )
                try:
                    trigger_payout(db=db, pool=pool)
                except Exception as e:
                    print(
                        f"[PayoutFinalizer] Retry failed for stuck pool "
                        f"{pool.id}: {e}. Will retry again next run."
                    )

    except Exception as e:
        print(f"[PayoutFinalizer] Error: {e}")
    finally:
        db.close()


def register_payout_finalizer_job(scheduler) -> None:
    """
    Adds the payout-finalizer job to an existing APScheduler instance.
    Called from background/pool_expiry_checker.py's create_scheduler()
    (or directly from main.py) so there is one scheduler for the whole
    app rather than two competing ones.
    """
    scheduler.add_job(
        run_payout_finalizer,
        trigger=IntervalTrigger(minutes=5),
        id="payout_finalizer",
        name="Pending Payout Finalizer",
        replace_existing=True,
    )
