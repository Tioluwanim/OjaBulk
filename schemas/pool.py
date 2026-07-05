"""
schemas/pool.py

Pydantic schemas for Pool endpoints.

Same split principle as trader.py: PoolCreate never includes
current_locked_amount or status — those are backend-controlled state,
never client input.

IMPORTANT: every Response schema must set model_config = ConfigDict(from_attributes=True).
This was missing on ContributorResponse and PoolJoinResponse — fixed below.
Rule going forward: any schema used as a `response_model` in a router,
or constructed anywhere from a SQLAlchemy object rather than plain kwargs,
must have this set. Schemas that are pure request input (Create, JoinRequest)
do NOT need it, since they are never built from ORM objects.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PoolCreate(BaseModel):
    """
    What a Head of Traders (or admin) may submit to POST /pools —
    request input, no from_attributes needed.

    market_name is REQUIRED. A Head of Traders can only submit a
    market_name matching their own Identity.market_name — enforced in
    routers/pools.py, not here, since this schema has no knowledge of
    who is making the request.
    """
    title: str = Field(..., min_length=3, max_length=200)
    market_name: str = Field(..., min_length=2, max_length=200)
    target_amount: float = Field(..., gt=0)
    supplier_name: str = Field(..., min_length=2, max_length=200)
    supplier_account_number: str = Field(..., min_length=10, max_length=10)
    supplier_bank_code: str = Field(..., min_length=1, max_length=10)
    deadline: datetime

    @field_validator("supplier_account_number")
    @classmethod
    def validate_nuban(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("supplier_account_number must be a 10-digit NUBAN")
        return v

    @field_validator("title", "supplier_name", "market_name")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class PoolJoinRequest(BaseModel):
    """What a client sends to POST /pools/{id}/join — request input, no from_attributes needed"""
    trader_id: str


class ContributorResponse(BaseModel):
    """Fixed: added from_attributes=True — this schema is built per-item in a list comprehension
    in the pools router; if that construction path ever changes to pass an ORM object
    directly, this prevents the same class of error as LedgerEntryResponse."""
    model_config = ConfigDict(from_attributes=True)

    trader_id: str
    amount_locked: float
    status: str
    created_at: datetime


class PoolResponse(BaseModel):
    """What we return for a single pool"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    market_name: str | None = None
    target_amount: float
    current_locked_amount: float
    progress_pct: float
    supplier_name: str
    supplier_account_number: str
    supplier_bank_code: str
    status: str
    deadline: datetime
    created_at: datetime | None = None
    fulfilled_at: datetime | None = None
    wholesaler_confirmed_at: datetime | None = None


class PoolDetailResponse(PoolResponse):
    """Pool response with contributor breakdown — used for GET /pools/{id}.
    Inherits model_config from PoolResponse automatically."""
    contributors: list[ContributorResponse] = []


class PoolJoinResponse(BaseModel):
    """Fixed: added from_attributes=True for consistency, even though this is
    currently always constructed from plain kwargs in the router."""
    model_config = ConfigDict(from_attributes=True)

    message: str
    trader_id: str
    pool_id: str
    pool_title: str
    target: float
    progress: float


class WholesalerConfirmResponse(BaseModel):
    """
    Returned by POST /pools/{id}/confirm-order — the wholesaler
    acknowledging they have received the payout and will fulfil the
    order. Kept intentionally separate from PoolResponse rather than
    reusing it, since this endpoint's whole purpose is a single new
    piece of state (wholesaler_confirmed_at), not the full pool shape.
    """
    model_config = ConfigDict(from_attributes=True)

    pool_id: str
    pool_title: str
    wholesaler_confirmed_at: datetime
    message: str
