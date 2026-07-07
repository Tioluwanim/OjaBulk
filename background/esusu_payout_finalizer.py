"""
background/esusu_payout_finalizer.py

Periodic background job -- requeries Nomba for any Esusu round whose
beneficiary bank-transfer payout was accepted (201/PROCESSING) but not
yet confirmed, and finalizes it once Nomba reports a final status.

Mirrors background/payout_finalizer.py's role for Pool payouts. See
services/esusu.py's _credit_beneficiary_via_bank_transfer() and
finalize_pending_esusu_payout() for why this exists: a round is only
left in EsusuRoundStatus.PAYOUT_PROCESSING when the beneficiary has
real payout bank details on file and Nomba's transfer to them hasn't
settled yet.
"""

from datetime import datetime, timezone
from apscheduler.triggers.interval import IntervalTrigger

from core.database import SessionLocal
from models.esusu import EsusuRound, EsusuRoundStatus
from services.esusu import finalize_pending_esusu_payout


async def run_esusu_payout_finalizer():
    print(f"[EsusuPayoutFinalizer] Running at {datetime.now(timezone.utc).isoformat()}")
    db = SessionLocal()
    try:
        pending_rounds = (
            db.query(EsusuRound)
            .filter(EsusuRound.status == EsusuRoundStatus.PAYOUT_PROCESSING)
            .all()
        )

        if not pending_rounds:
            print("[EsusuPayoutFinalizer] No rounds pending payout confirmation")
            return

        for round_row in pending_rounds:
            try:
                finalize_pending_esusu_payout(db, round_row)
            except Exception as e:
                print(f"[EsusuPayoutFinalizer] Error finalizing round {round_row.id}: {e}")

    except Exception as e:
        print(f"[EsusuPayoutFinalizer] Error: {e}")
    finally:
        db.close()


def register_esusu_payout_finalizer_job(scheduler) -> None:
    """
    Adds the Esusu-payout-finalizer job to an existing APScheduler
    instance. Called from background/pool_expiry_checker.py's
    create_scheduler() so there is one scheduler for the whole app.
    """
    scheduler.add_job(
        run_esusu_payout_finalizer,
        trigger=IntervalTrigger(minutes=5),
        id="esusu_payout_finalizer",
        name="Pending Esusu Payout Finalizer",
        replace_existing=True,
    )
