"""
routers/pools.py

Pool creation, listing, joining, and detail endpoints.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

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

# ... [create_pool logic remains the same] ...
@router.post("", response_model=PoolResponse, status_code=201)
def create_pool(payload: PoolCreate, db: Session = Depends(get_db)):
    deadline = payload.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="deadline must be in the future")
    pool = Pool(
        title=payload.title,
        target_amount=Decimal(str(payload.target_amount)),
        supplier_name=payload.supplier_name,
        supplier_account_number=payload.supplier_account_number,
        supplier_bank_code=payload.supplier_bank_code,
        deadline=deadline,
        status=PoolStatus.OPEN,
        current_locked_amount=Decimal("0"),
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)
    return _pool_response(pool)

@router.get("", response_model=list[PoolResponse])
def list_pools(db: Session = Depends(get_db)):
    pools: list[Pool] = db.query(Pool).order_by(desc(Pool.created_at)).all()  # type: ignore
    return [_pool_response(p) for p in pools]

@router.get("/{pool_id}", response_model=PoolDetailResponse)
def get_pool(pool_id: uuid.UUID, db: Session = Depends(get_db)):
    # .filter() lines often trigger the "Expected ColumnElement" error
    pool: Pool | None = db.query(Pool).filter(Pool.id == pool_id).first()  # type: ignore
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    contributions: list[PoolContribution] = db.query(PoolContribution).filter(  # type: ignore
        PoolContribution.pool_id == pool_id
    ).all()

    base = _pool_response(pool)
    return PoolDetailResponse(
        **base.model_dump(),
        contributors=[
            ContributorResponse(
                trader_id=str(c.trader_id),
                amount_locked=float(c.amount_locked),
                status=c.status.value if hasattr(c.status, "value") else str(c.status),
                created_at=c.created_at,
            )
            for c in contributions
        ],
    )

@router.post("/{pool_id}/check-expiry")
def manually_check_expiry(pool_id: uuid.UUID, db: Session = Depends(get_db)):
    pool: Pool | None = db.query(Pool).filter(Pool.id == pool_id).first()  # type: ignore
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # Using explicit status comparison
    if pool.status == PoolStatus.OPEN and pool.deadline < datetime.now(timezone.utc):  # type: ignore
        result = refund_pool(db=db, pool=pool)
        return {"message": "Pool expired and refunded", "details": result}
    return {"message": "Pool is either not open or deadline has not passed"}

@router.post("/{pool_id}/join", response_model=PoolJoinResponse)
def join_pool(pool_id: uuid.UUID, payload: PoolJoinRequest, db: Session = Depends(get_db)):
    try:
        trader_uuid = uuid.UUID(payload.trader_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="trader_id must be a valid UUID")

    pool: Pool | None = db.query(Pool).filter(Pool.id == pool_id).first()  # type: ignore
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.status != PoolStatus.OPEN:  # type: ignore
        raise HTTPException(status_code=400, detail=f"Pool is {pool.status.value} — cannot join")

    trader: Trader | None = db.query(Trader).filter(Trader.id == trader_uuid).first()  # type: ignore
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    existing: PoolContribution | None = db.query(PoolContribution).filter(  # type: ignore
        PoolContribution.trader_id == trader_uuid,
        PoolContribution.pool_id == pool_id,
        PoolContribution.status == ContributionStatus.LOCKED,
    ).first()

    if existing:
        return PoolJoinResponse(
            message=f"{trader.name} is already contributing",
            trader_id=payload.trader_id,
            pool_id=str(pool_id),
            pool_title=pool.title,
            target=float(pool.target_amount),
            progress=_progress_pct(pool),
        )

    contribution = PoolContribution(
        trader_id=trader_uuid,
        pool_id=pool_id,
        amount_locked=Decimal("0"),
        status=ContributionStatus.LOCKED,
    )
    db.add(contribution)
    db.commit()
    return PoolJoinResponse(
        message=f"{trader.name} joined {pool.title}",
        trader_id=payload.trader_id,
        pool_id=str(pool_id),
        pool_title=pool.title,
        target=float(pool.target_amount),
        progress=_progress_pct(pool),
    )

def _progress_pct(pool: Pool) -> float:
    if pool.target_amount <= Decimal("0"):
        return 0.0
    return round((float(pool.current_locked_amount) / float(pool.target_amount)) * 100, 2)

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
        status=pool.status.value if hasattr(pool.status, "value") else str(pool.status),
        deadline=pool.deadline,
        created_at=pool.created_at,
        fulfilled_at=pool.fulfilled_at,
    )