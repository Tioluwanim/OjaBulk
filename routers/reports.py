"""
routers/reports.py

Reconciliation report — the demo differentiator.
Now returns a typed ReconciliationResponse instead of a raw dict.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.database import get_db
from models.trader import Trader
from models.pool import Pool, PoolStatus
from services.reports import reports_service
from schemas.reports import (
    ReconciliationResponse,
    ReconciliationBreakdown,
    StatsResponse,
)

router = APIRouter()


@router.get("/reconciliation", response_model=ReconciliationResponse)
def get_reconciliation_report(db: Session = Depends(get_db)):
    """
    GET /reports/reconciliation

    Compares our PostgreSQL ledger total (spendable + locked)
    against the real Nomba account balance.
    """
    spendable_total = db.query(
        func.coalesce(func.sum(Trader.spendable_balance), 0)
    ).scalar() or 0

    locked_total = db.query(
        func.coalesce(func.sum(Pool.current_locked_amount), 0)
    ).filter(Pool.status == PoolStatus.OPEN).scalar() or 0

    our_ledger_total = float(spendable_total) + float(locked_total)
    breakdown = ReconciliationBreakdown(
        spendable_total=float(spendable_total),
        locked_total=float(locked_total),
    )

    try:
        reconciliation = reports_service.reconcile(our_ledger_total)
    except Exception as e:
        return ReconciliationResponse(
            error=str(e),
            our_ledger_total=our_ledger_total,
            breakdown=breakdown,
        )

    return ReconciliationResponse(
        nomba_balance=reconciliation["nomba_balance"],
        our_ledger_total=reconciliation["our_ledger_total"],
        discrepancy=reconciliation["discrepancy"],
        is_reconciled=reconciliation["is_reconciled"],
        currency=reconciliation["currency"],
        checked_at=reconciliation["checked_at"],
        breakdown=breakdown,
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """
    GET /reports/stats
    Summary stats for the admin dashboard top row.
    """
    total_traders = db.query(func.count(Trader.id)).scalar() or 0
    active_pools = db.query(func.count(Pool.id)).filter(
        Pool.status == PoolStatus.OPEN
    ).scalar() or 0
    fulfilled_pools = db.query(func.count(Pool.id)).filter(
        Pool.status == PoolStatus.FULFILLED
    ).scalar() or 0

    total_locked = db.query(
        func.coalesce(func.sum(Pool.current_locked_amount), 0)
    ).filter(Pool.status == PoolStatus.OPEN).scalar() or 0

    total_fulfilled_amount = db.query(
        func.coalesce(func.sum(Pool.current_locked_amount), 0)
    ).filter(Pool.status == PoolStatus.FULFILLED).scalar() or 0

    return StatsResponse(
        total_traders=total_traders,
        active_pools=active_pools,
        fulfilled_pools=fulfilled_pools,
        total_locked=float(total_locked),
        total_fulfilled_amount=float(total_fulfilled_amount),
    )
