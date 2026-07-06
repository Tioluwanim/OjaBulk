"""
schemas/reports.py

Pydantic schemas for reconciliation report and dashboard stats.
These are response-only — no client input on these endpoints.

model_config = ConfigDict(from_attributes=True) added defensively on all
schemas here, even though nothing currently constructs them from ORM
objects. This matches the fix applied to trader.py and pool.py and
prevents this same bug class from appearing if these schemas are ever
constructed differently in the future.
"""

from pydantic import BaseModel, ConfigDict


class ReconciliationBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spendable_total: float
    locked_total: float


class ReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nomba_balance: float | None = None
    our_ledger_total: float
    discrepancy: float | None = None
    is_reconciled: bool | None = None
    currency: str | None = None
    checked_at: str | None = None
    breakdown: ReconciliationBreakdown
    error: str | None = None


class StatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_traders: int
    active_pools: int
    fulfilled_pools: int
    total_locked: float
    total_fulfilled_amount: float


class RecentPaymentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trader_id: str
    trader_name: str
    trader_phone: str
    amount_received: float
    spendable_portion: float
    pool_portion: float
    pool_id: str | None = None
    pool_title: str | None = None
    nomba_transaction_ref: str
    received_at: str | None = None


class RecentPaymentsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[RecentPaymentItem]


class AnalyticsSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    open_pools: int
    fulfilled_pools: int
    refunded_pools: int
    total_locked_open_pools: float
    average_open_pool_progress_pct: float
    near_target_pools: int
