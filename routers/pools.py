"""
routers/pools.py

Pool creation, listing, joining, and detail endpoints.
Now uses Pydantic schemas for request validation and response shaping.
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models.pool import Pool, PoolStatus
from models.pool_contribution import PoolContribution, ContributionStatus
from models.trader import Trader
from engine.refund import refund_pool
from schemas.pool import (
    PoolCreate,
    PoolResponse,
    PoolDetailResponse,
    PoolJoinRequest,
    PoolJoinResponse,
    ContributorResponse,
)

router = APIRouter()


@router.post("", response_model=PoolResponse, status_code=201)
def create_pool(payload: PoolCreate, db: Session = Depends(get_db)):
    """
    POST /pools
    Admin creates a bulk-buying pool.
    Pydantic validates target_amount > 0, NUBAN format, and deadline type.
    """
    deadline = payload.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if deadline <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="deadline must be in the future")

    pool = Pool(
        title=payload.title,
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
def list_pools(db: Session = Depends(get_db)):
    """GET /pools — all pools with progress"""
    pools = db.query(Pool).order_by(Pool.created_at.desc()).all()
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
def join_pool(pool_id: str, payload: PoolJoinRequest, db: Session = Depends(get_db)):
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
    )
