"""
routers/pools.py

Pool creation, listing, joining, and detail endpoints.

AUTH ADDED: create_pool now requires a HEAD_OF_TRADERS identity, and
enforces that they may only create pools for their OWN market_name —
the market-scoping rule is checked HERE, against identity.market_name
from the verified session token, never against a market_name the
client could freely type into the request body to bypass the rule.

confirm_order is a NEW endpoint for wholesalers — see schemas/pool.py's
WholesalerConfirmResponse docstring for why this is a separate action
rather than folded into GET /pools/{id}.
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models.pool import Pool, PoolStatus
from models.pool_contribution import PoolContribution, ContributionStatus
from models.trader import Trader
from models.identity import Identity, IdentityRole
from engine.refund import refund_pool
from services.auth import require_role, get_current_identity, get_current_identity_optional
from schemas.pool import (
    PoolCreate,
    PoolResponse,
    PoolDetailResponse,
    PoolJoinRequest,
    PoolJoinResponse,
    ContributorResponse,
    WholesalerConfirmResponse,
)

router = APIRouter()


@router.post("", response_model=PoolResponse, status_code=201)
def create_pool(
    payload: PoolCreate,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_role(IdentityRole.HEAD_OF_TRADERS)),
):
    """
    POST /pools
    Head of Traders creates a bulk-buying pool for THEIR OWN market only.

    MARKET-SCOPING RULE: payload.market_name must exactly match
    identity.market_name (the market this Head of Traders is actually
    registered for, from their verified session token) — not whatever
    market_name they typed in the request body. A Head of Onitsha
    Market cannot create a pool for Alaba Market by simply typing a
    different market_name in the payload.
    """
    if payload.market_name != identity.market_name:
        raise HTTPException(
            status_code=403,
            detail=(
                f"You are registered as Head of Traders for "
                f"'{identity.market_name}'. You cannot create pools "
                f"for '{payload.market_name}'."
            )
        )

    deadline = payload.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if deadline <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="deadline must be in the future")

    pool = Pool(
        title=payload.title,
        market_name=payload.market_name,
        created_by_identity_id=identity.id,
        target_amount=payload.target_amount,
        supplier_name=payload.supplier_name,
        supplier_account_number=payload.supplier_account_number,
        supplier_bank_code=payload.supplier_bank_code,
        deadline=deadline,
        status=PoolStatus.OPEN,
        current_locked_amount=0,
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)

    return _pool_response(pool)


@router.get("", response_model=list[PoolResponse])
def list_pools(
    supplier: str | None = None,
    db: Session = Depends(get_db),
    identity: Identity | None = Depends(get_current_identity_optional),
):
    """
    GET /pools — all pools with progress.

    GET /pools?supplier=me — WHOLESALER-SCOPED VIEW. Requires a valid
    wholesaler session token (Authorization header). Returns only
    pools where pool.supplier_name matches the wholesaler's
    Identity.business_name — the same string-match ownership rule
    used by confirm_order below, kept consistent between the two.

    Without ?supplier=me, this route stays PUBLIC and unfiltered —
    that behaviour is unchanged from before this endpoint existed.
    Any other value of ?supplier= is rejected with 422 rather than
    silently ignored, since a typo here should be visible, not silent.
    """
    if supplier is None:
        pools = db.query(Pool).order_by(Pool.created_at.desc()).all()
        return [_pool_response(p) for p in pools]

    if supplier != "me":
        raise HTTPException(
            status_code=422,
            detail="supplier query param only accepts the value 'me'."
        )

    if identity is None:
        raise HTTPException(
            status_code=401,
            detail=(
                "supplier=me requires a valid wholesaler session token "
                "in the Authorization header."
            )
        )

    if identity.role != IdentityRole.WHOLESALER:
        raise HTTPException(
            status_code=403,
            detail=(
                f"supplier=me is only available to wholesaler logins. "
                f"You are logged in as {identity.role.value}."
            )
        )

    pools = (
        db.query(Pool)
        .filter(Pool.supplier_name == identity.business_name)
        .order_by(Pool.created_at.desc())
        .all()
    )
    return [_pool_response(p) for p in pools]


@router.get("/{pool_id}", response_model=PoolDetailResponse)
def get_pool(pool_id: str, db: Session = Depends(get_db)):
    """
    GET /pools/{id}
    Returns pool detail. Also triggers on-demand expiry check —
    if the pool is past its deadline and still open, refund it now.
    """
    try:
        pool_uuid = uuid.UUID(pool_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="pool_id must be a valid UUID")

    pool = db.query(Pool).filter(Pool.id == pool_uuid).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # Defensive: ensure deadline is timezone-aware before comparing.
    # Some DB drivers return naive datetimes even when the column is
    # timezone-aware, which crashes this comparison with a TypeError.
    pool_deadline = pool.deadline
    if pool_deadline.tzinfo is None:
        pool_deadline = pool_deadline.replace(tzinfo=timezone.utc)

    if (
        pool.status == PoolStatus.OPEN
        and pool_deadline < datetime.now(timezone.utc)
    ):
        refund_pool(db=db, pool=pool)
        db.refresh(pool)

    contributions = db.query(PoolContribution).filter(
        PoolContribution.pool_id == pool_uuid
    ).all()

    base = _pool_response(pool)
    return PoolDetailResponse(
        **base.model_dump(),
        contributors=[
            ContributorResponse(
                trader_id=str(c.trader_id),
                amount_locked=float(c.amount_locked),
                status=str(c.status.value),
                created_at=c.created_at,
            )
            for c in contributions
        ],
    )


@router.post("/{pool_id}/join", response_model=PoolJoinResponse)
def join_pool(
    pool_id: str,
    payload: PoolJoinRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_role(IdentityRole.TRADER)),
):
    """
    POST /pools/{id}/join
    Trader opts into a pool as their active contribution target.
    Does NOT move money — just sets this pool as the target for future payments.
    """
    try:
        pool_uuid = uuid.UUID(pool_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="pool_id must be a valid UUID")

    try:
        trader_uuid = uuid.UUID(payload.trader_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="trader_id must be a valid UUID")

    pool = db.query(Pool).filter(Pool.id == pool_uuid).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if pool.status != PoolStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail=f"Pool is {pool.status.value} — cannot join a closed pool"
        )

    trader = db.query(Trader).filter(Trader.id == trader_uuid).first()
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    if identity.linked_trader_id is None:
        raise HTTPException(
            status_code=404,
            detail="This trader identity is not linked to a trader record."
        )

    if identity.linked_trader_id != trader_uuid:
        raise HTTPException(
            status_code=403,
            detail="You can only join pools for your own trader account."
        )

    if pool.market_name and trader.market_name != pool.market_name:
        raise HTTPException(
            status_code=403,
            detail=(
                f"This pool is for {pool.market_name}, but your trader "
                f"record belongs to {trader.market_name}."
            )
        )

    existing = db.query(PoolContribution).filter(
        PoolContribution.trader_id == trader_uuid,
        PoolContribution.pool_id == pool_uuid,
        PoolContribution.status == ContributionStatus.LOCKED,
    ).first()
    if existing:
        return PoolJoinResponse(
            message=f"{trader.name} is already contributing to this pool",
            trader_id=payload.trader_id,
            pool_id=pool_id,
            pool_title=pool.title,
            target=float(pool.target_amount),
            progress=_progress_pct(pool),
        )

    contribution = PoolContribution(
        trader_id=trader_uuid,
        pool_id=pool_uuid,
        amount_locked=0,
        status=ContributionStatus.LOCKED,
    )
    db.add(contribution)
    db.commit()

    return PoolJoinResponse(
        message=f"{trader.name} joined {pool.title}",
        trader_id=payload.trader_id,
        pool_id=pool_id,
        pool_title=pool.title,
        target=float(pool.target_amount),
        progress=_progress_pct(pool),
    )


@router.post("/{pool_id}/confirm-order", response_model=WholesalerConfirmResponse)
def confirm_order(
    pool_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_role(IdentityRole.WHOLESALER)),
):
    """
    POST /pools/{id}/confirm-order

    Wholesaler confirms they have received the payout and will fulfil
    the order. Only callable on a FULFILLED pool — a wholesaler cannot
    confirm an order for a pool that hasn't actually paid out yet.

    OWNERSHIP CHECK: the wholesaler's Identity.business_name must
    match the pool's supplier_name, otherwise any wholesaler could
    confirm any other wholesaler's order. This is a simple string
    match rather than a rigid foreign key, matching the design
    decision documented in models/identity.py — the same wholesaler
    identity can legitimately supply many different pools over time
    without a fixed pool-to-wholesaler link existing anywhere.
    """
    try:
        pool_uuid = uuid.UUID(pool_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="pool_id must be a valid UUID")

    pool = db.query(Pool).filter(Pool.id == pool_uuid).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.status != PoolStatus.FULFILLED:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Pool is {pool.status.value} — orders can only be "
                f"confirmed on fulfilled pools."
            )
        )

    if identity.business_name != pool.supplier_name:
        raise HTTPException(
            status_code=403,
            detail=(
                f"This pool's supplier is '{pool.supplier_name}', "
                f"but you are registered as '{identity.business_name}'. "
                f"You can only confirm orders for your own pools."
            )
        )

    if pool.wholesaler_confirmed_at is not None:
        raise HTTPException(
            status_code=400,
            detail="This order has already been confirmed."
        )

    pool.wholesaler_confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pool)

    return WholesalerConfirmResponse(
        pool_id=str(pool.id),
        pool_title=pool.title,
        wholesaler_confirmed_at=pool.wholesaler_confirmed_at,
        message=f"Order confirmed for {pool.title}. Thank you.",
    )


def _progress_pct(pool: Pool) -> float:
    if pool.target_amount <= 0:
        return 0.0
    return round(
        (float(pool.current_locked_amount) / float(pool.target_amount)) * 100, 2
    )


def _pool_response(pool: Pool) -> PoolResponse:
    return PoolResponse(
        id=str(pool.id),
        title=pool.title,
        market_name=pool.market_name,
        target_amount=float(pool.target_amount),
        current_locked_amount=float(pool.current_locked_amount),
        progress_pct=_progress_pct(pool),
        supplier_name=pool.supplier_name,
        supplier_account_number=pool.supplier_account_number,
        supplier_bank_code=pool.supplier_bank_code,
        status=str(pool.status.value),
        deadline=pool.deadline,
        created_at=pool.created_at,
        fulfilled_at=pool.fulfilled_at,
        wholesaler_confirmed_at=pool.wholesaler_confirmed_at,
    )
