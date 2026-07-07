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
from engine.payout import finalize_pending_payout


async def run_payout_finalizer():
    """
    Finds every pool sitting in PAYOUT_PROCESSING and requeries Nomba
    for each one. Runs every 5 minutes — frequent enough that a demo
    or a real trader isn't left wondering for long, without hammering
    Nomba's requery endpoint.
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
            return

        for pool in pending_pools:
            try:
                finalize_pending_payout(db, pool)
            except Exception as e:
                print(f"[PayoutFinalizer] Error finalizing pool {pool.id}: {e}")

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
