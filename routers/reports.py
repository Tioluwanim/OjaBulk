"""
routers/reports.py

Reconciliation report — the demo differentiator.
Now returns a typed ReconciliationResponse instead of a raw dict.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from core.database import get_db
from models.payment import Payment
from models.trader import Trader
from models.ledger_entry import LedgerEntry, EntryType
from models.pool import Pool, PoolStatus
from services.reports import reports_service
from schemas.reports import (
    ReconciliationResponse,
    ReconciliationBreakdown,
    StatsResponse,
    RecentPaymentsResponse,
    RecentPaymentItem,
    AnalyticsSummaryResponse,
)

router = APIRouter()


@router.get("/reconciliation", response_model=ReconciliationResponse)
def get_reconciliation_report(db: Session = Depends(get_db)):
    """
    GET /reports/reconciliation

    Compares our PostgreSQL ledger total derived from ledger entry types
    against the real Nomba account balance.
    """
    spendable_total = db.query(
        func.coalesce(
            func.sum(
                case(
                    (
                        LedgerEntry.entry_type == EntryType.SPENDABLE_CREDIT,
                        LedgerEntry.amount,
                    ),
                    (
                        LedgerEntry.entry_type == EntryType.POOL_REFUND,
                        LedgerEntry.amount,
                    ),
                    else_=0,
                )
            ),
            0,
        )
    ).scalar() or 0

    locked_in_total = db.query(
        func.coalesce(
            func.sum(
                case(
                    (
                        LedgerEntry.entry_type == EntryType.POOL_LOCK,
                        LedgerEntry.amount,
                    ),
                    else_=0,
                )
            ),
            0,
        )
    ).scalar() or 0

    released_total = db.query(
        func.coalesce(
            func.sum(
                case(
                    (
                        LedgerEntry.entry_type == EntryType.POOL_RELEASE_PAYOUT,
                        LedgerEntry.amount,
                    ),
                    else_=0,
                )
            ),
            0,
        )
    ).scalar() or 0

    locked_total = float(locked_in_total) - float(released_total)

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


@router.get("/recent-payments", response_model=RecentPaymentsResponse)
def get_recent_payments(db: Session = Depends(get_db)):
    """
    GET /reports/recent-payments

    Returns the most recent payment rows for dashboard feeds.
    """
    payments = (
        db.query(Payment, Trader, Pool)
        .join(Trader, Trader.id == Payment.trader_id)
        .outerjoin(Pool, Pool.id == Payment.pool_id)
        .order_by(Payment.received_at.desc())
        .limit(10)
        .all()
    )

    return RecentPaymentsResponse(
        items=[
            RecentPaymentItem(
                id=str(payment.id),
                trader_id=str(trader.id),
                trader_name=trader.name,
                trader_phone=trader.phone,
                amount_received=float(payment.amount_received),
                spendable_portion=float(payment.spendable_portion or 0),
                pool_portion=float(payment.pool_portion or 0),
                pool_id=str(pool.id) if pool else None,
                pool_title=pool.title if pool else None,
                nomba_transaction_ref=payment.nomba_transaction_ref,
                received_at=payment.received_at.isoformat() if payment.received_at else None,
            )
            for payment, trader, pool in payments
        ]
    )


@router.get("/payments/recent", response_model=RecentPaymentsResponse)
def get_recent_payments_alias(db: Session = Depends(get_db)):
    """
    Compatibility alias for the MVP guide's GET /payments/recent reference.
    """
    return get_recent_payments(db=db)


@router.get("/stats", response_model=StatsResponse, include_in_schema=False)
def get_stats_alias(db: Session = Depends(get_db)):
    """
    Compatibility alias for the MVP guide's GET /stats reference.
    """
    return get_stats(db=db)


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(db: Session = Depends(get_db)):
    """
    GET /analytics/summary

    Lightweight pool health summary for the dashboard AI panel.
    """
    open_pools = db.query(func.count(Pool.id)).filter(
        Pool.status == PoolStatus.OPEN
    ).scalar() or 0
    fulfilled_pools = db.query(func.count(Pool.id)).filter(
        Pool.status == PoolStatus.FULFILLED
    ).scalar() or 0
    refunded_pools = db.query(func.count(Pool.id)).filter(
        Pool.status == PoolStatus.REFUNDED
    ).scalar() or 0

    open_pool_rows = db.query(Pool).filter(Pool.status == PoolStatus.OPEN).all()
    total_locked_open_pools = float(
        sum(float(pool.current_locked_amount or 0) for pool in open_pool_rows)
    )
    average_open_pool_progress_pct = 0.0
    near_target_pools = 0

    if open_pool_rows:
        progress_values = []
        for pool in open_pool_rows:
            target_amount = float(pool.target_amount or 0)
            locked_amount = float(pool.current_locked_amount or 0)
            if target_amount > 0:
                progress = (locked_amount / target_amount) * 100
                progress_values.append(progress)
                if progress >= 80:
                    near_target_pools += 1
        if progress_values:
            average_open_pool_progress_pct = round(sum(progress_values) / len(progress_values), 2)

    return AnalyticsSummaryResponse(
        open_pools=open_pools,
        fulfilled_pools=fulfilled_pools,
        refunded_pools=refunded_pools,
        total_locked_open_pools=total_locked_open_pools,
        average_open_pool_progress_pct=average_open_pool_progress_pct,
        near_target_pools=near_target_pools,
    )