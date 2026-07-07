"""
background/pool_expiry_checker.py

Periodic background job — checks for expired pools and triggers refunds.
Also contains the Render ping job to keep the free tier alive.

Jobs:
    1. Pool expiry check — runs every 30 minutes
    2. Render ping — runs every 10 minutes (free tier sleeps after 15min inactivity)
"""

import asyncio
import httpx
import os
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.database import SessionLocal
from engine.refund import check_and_refund_expired_pools
from background.payout_finalizer import register_payout_finalizer_job
from background.esusu_payout_finalizer import register_esusu_payout_finalizer_job


# ── Job 1: Pool expiry checker ─────────────────────────────────────────────

async def run_pool_expiry_check():
    """
    Finds all open pools past their deadline and refunds all contributors.
    Runs every 30 minutes.
    """
    print(f"[PoolExpiryChecker] Running at {datetime.now(timezone.utc).isoformat()}")
    db = SessionLocal()
    try:
        results = check_and_refund_expired_pools(db)
        if results:
            print(f"[PoolExpiryChecker] Processed {len(results)} expired pool(s)")
        else:
            print(f"[PoolExpiryChecker] No expired pools found")
    except Exception as e:
        print(f"[PoolExpiryChecker] Error: {e}")
    finally:
        db.close()


# ── Job 2: Render ping (keeps free tier alive) ─────────────────────────────

RENDER_APP_URL = os.getenv("RENDER_APP_URL", "")

async def ping_self():
    """
    Pings OjaBulk's own /ping endpoint every 10 minutes.
    Render free tier spins down after 15 minutes of inactivity.
    This keeps it alive during the hackathon demo period.
    """
    if not RENDER_APP_URL:
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{RENDER_APP_URL}/ping")
            print(
                f"[Ping] {datetime.now(timezone.utc).strftime('%H:%M:%S')} "
                f"→ {response.status_code}"
            )
    except Exception as e:
        print(f"[Ping] Failed: {e}")


# ── Scheduler setup ────────────────────────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    """
    Creates and configures the APScheduler instance.
    Called once at app startup in main.py lifespan.
    """
    scheduler = AsyncIOScheduler()

    # Pool expiry check — every 30 minutes
    scheduler.add_job(
        run_pool_expiry_check,
        trigger=IntervalTrigger(minutes=30),
        id="pool_expiry_check",
        name="Pool Expiry Checker",
        replace_existing=True,
    )

    # Render ping — every 10 minutes
    scheduler.add_job(
        ping_self,
        trigger=IntervalTrigger(minutes=10),
        id="render_ping",
        name="Render Keep-Alive Ping",
        replace_existing=True,
    )

    # Pending payout finalizer — every 5 minutes
    register_payout_finalizer_job(scheduler)

    # Pending Esusu payout finalizer — every 5 minutes
    register_esusu_payout_finalizer_job(scheduler)

    return scheduler
