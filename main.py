"""
main.py

OjaBulk FastAPI application entrypoint.

Startup sequence:
    1. Database tables created (if not exist)
    2. APScheduler started (pool expiry + Render ping)
    3. All routers mounted

Shutdown sequence:
    1. APScheduler stopped cleanly
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import engine, Base
from background.pool_expiry_checker import create_scheduler

# Import all models so Base.metadata.create_all picks them up
import models  # noqa: F401

# Import routers
from routers import traders, pools, webhooks, reports, ussd


# ── Lifespan (startup + shutdown) ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[OjaBulk] Starting up...")

    # Create all DB tables
    Base.metadata.create_all(bind=engine)
    print("[OjaBulk] Database tables ready")

    # Start background scheduler
    scheduler = create_scheduler()
    scheduler.start()
    print("[OjaBulk] Background scheduler started")
    print("[OjaBulk]   - Pool expiry check: every 30 minutes")
    print("[OjaBulk]   - Render ping:       every 10 minutes")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    print("[OjaBulk] Scheduler stopped. Goodbye.")


# ── App instance ───────────────────────────────────────────────────────────

app = FastAPI(
    title="OjaBulk API",
    description=(
        "Smart pooled procurement infrastructure for Nigerian market traders. "
        "Build Track: Virtual Accounts as Infrastructure — Nomba Hackathon 2026."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS ───────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",           # Next.js dev
        "https://ojabulk.vercel.app",      # Frontend production
        "*",                               # Open during hackathon — tighten post-demo
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ────────────────────────────────────────────────────────────────

app.include_router(traders.router,  prefix="/traders",          tags=["Traders"])
app.include_router(pools.router,    prefix="/pools",            tags=["Pools"])
app.include_router(webhooks.router, prefix="/webhooks",         tags=["Webhooks"])
app.include_router(reports.router,  prefix="/reports",          tags=["Reports"])
app.include_router(ussd.router,     prefix="/ussd",             tags=["USSD"])


# ── Health + ping endpoints ────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "product":     "OjaBulk",
        "status":      "running",
        "description": "Smart pooled procurement for Nigerian market traders",
        "track":       "Virtual Accounts as Infrastructure — Nomba Hackathon 2026",
    }


@app.get("/ping", tags=["Health"])
async def ping():
    """
    Keep-alive endpoint pinged by the background scheduler
    to prevent Render free tier from spinning down.
    """
    from datetime import datetime, timezone
    return {
        "status": "ok",
        "time":   datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health", tags=["Health"])
async def health():
    """
    Detailed health check — verifies DB connection and Nomba auth.
    """
    from core.database import SessionLocal
    from services.client import nomba_client
    from sqlalchemy import text

    db_ok = False
    nomba_ok = False

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception as e:
        print(f"[Health] DB check failed: {e}")

    try:
        nomba_client.get_token()
        nomba_ok = True
    except Exception as e:
        print(f"[Health] Nomba auth check failed: {e}")

    return {
        "database": "ok" if db_ok else "error",
        "nomba":    "ok" if nomba_ok else "error",
        "overall":  "ok" if (db_ok and nomba_ok) else "degraded",
    }
