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
