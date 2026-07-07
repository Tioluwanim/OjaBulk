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
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models.pool import Pool, PoolStatus
from models.pool_contribution import PoolContribution, ContributionStatus
from models.trader import Trader
from models.identity import Identity, IdentityRole
from models.ledger_entry import LedgerEntry, EntryType
from engine.refund import refund_pool
from engine.payout import trigger_payout
from services.auth import require_role, get_current_identity, get_current_identity_optional
from routers.auth import verify_admin_key
from schemas.pool import (
    PoolCreate,
    PoolUpdate,
    PoolResponse,
    PoolDetailResponse,
    PoolJoinRequest,
    PoolJoinResponse,
    PoolContributeFromSpendableRequest,
    PoolContributeFromSpendableResponse,
    PoolRetryPayoutResponse,
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


@router.post("/{pool_id}/contribute-from-spendable", response_model=PoolContributeFromSpendableResponse)
def contribute_from_spendable(
    pool_id: str,
    payload: PoolContributeFromSpendableRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_role(IdentityRole.TRADER)),
):
    """
    POST /pools/{id}/contribute-from-spendable

    Real gap this closes: the only way money ever locked into a pool
    was through engine/reconciliation.py's split, which only runs on a
    brand-new inbound Nomba payment. A trader with existing spendable
    balance (e.g. from an overpayment on a prior pool, or a payment
    made with no active pool selected) had no way to move that balance
    into a pool they've since joined — they'd have to send an entirely
    new bank transfer instead of using money already sitting in their
    OjaBulk wallet.

    Mirrors engine/reconciliation.py's locking pattern: row-locks the
    trader (same fix as the original row-locking audit finding) to
    prevent a race between two concurrent requests double-spending the
    same spendable balance, caps the amount locked at the pool's
    remaining gap (excess simply isn't moved, same as reconciliation's
    behavior — it stays spendable), writes a POOL_LOCK ledger entry,
    and triggers payout via the same trigger_payout() used everywhere
    else if this contribution completes the pool.
    """
    try:
        pool_uuid = uuid.UUID(pool_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="pool_id must be a valid UUID")

    if identity.linked_trader_id is None:
        raise HTTPException(status_code=404, detail="This identity is not linked to a trader record.")

    # Row-lock the trader for the duration of this transaction so two
    # concurrent contribute-from-spendable calls (or a race with a
    # webhook-driven reconcile()) can't both read the same
    # spendable_balance and double-spend it.
    trader = (
        db.query(Trader)
        .filter(Trader.id == identity.linked_trader_id)
        .with_for_update()
        .first()
    )
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    pool = (
        db.query(Pool)
        .filter(Pool.id == pool_uuid)
        .with_for_update()
        .first()
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if pool.status != PoolStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail=f"Pool is {pool.status.value} — cannot contribute to a closed pool",
        )

    requested = Decimal(str(payload.amount))
    current_spendable = Decimal(str(trader.spendable_balance))

    if requested > current_spendable:
        raise HTTPException(
            status_code=400,
            detail=(
                f"You only have ₦{current_spendable:,.2f} spendable, "
                f"cannot lock ₦{requested:,.2f}."
            ),
        )

    remaining_gap = max(
        Decimal("0"),
        Decimal(str(pool.target_amount)) - Decimal(str(pool.current_locked_amount)),
    )
    if remaining_gap <= 0:
        raise HTTPException(status_code=400, detail="This pool has already reached its target.")

    amount_to_lock = min(requested, remaining_gap)

    contribution = (
        db.query(PoolContribution)
        .filter(
            PoolContribution.trader_id == trader.id,
            PoolContribution.pool_id == pool_uuid,
            PoolContribution.status == ContributionStatus.LOCKED,
        )
        .first()
    )
    if not contribution:
        contribution = PoolContribution(
            trader_id=trader.id,
            pool_id=pool_uuid,
            amount_locked=0,
            status=ContributionStatus.LOCKED,
        )
        db.add(contribution)
        db.flush()

    contribution.amount_locked = float(
        Decimal(str(contribution.amount_locked)) + amount_to_lock
    )

    new_spendable = current_spendable - amount_to_lock
    trader.spendable_balance = float(new_spendable)

    pool.current_locked_amount = float(
        Decimal(str(pool.current_locked_amount)) + amount_to_lock
    )

    db.add(
        LedgerEntry(
            trader_id=trader.id,
            pool_id=pool.id,
            entry_type=EntryType.POOL_LOCK,
            amount=float(amount_to_lock),
            balance_after=float(new_spendable),
            note=(
                f"₦{amount_to_lock:,.2f} moved from spendable balance "
                f"and locked in {pool.title}"
            ),
        )
    )

    db.commit()
    db.refresh(pool)
    db.refresh(trader)

    pool_fulfilled = False
    if pool.status == PoolStatus.OPEN and Decimal(str(pool.current_locked_amount)) >= Decimal(str(pool.target_amount)):
        try:
            trigger_payout(db=db, pool=pool)
            pool_fulfilled = True
            db.refresh(pool)
        except Exception as e:
            print(f"[ContributeFromSpendable] Payout failed for pool {pool.id}: {e}")

    return PoolContributeFromSpendableResponse(
        pool_id=str(pool.id),
        trader_id=str(trader.id),
        amount_locked=float(amount_to_lock),
        new_spendable_balance=float(trader.spendable_balance),
        pool_current_locked_amount=float(pool.current_locked_amount),
        pool_fulfilled=pool_fulfilled,
        message=(
            f"₦{amount_to_lock:,.2f} locked in {pool.title}"
            + (" — pool fulfilled!" if pool_fulfilled else "")
        ),
    )


@router.patch("/{pool_id}", response_model=PoolResponse)
def update_pool(
    pool_id: str,
    payload: PoolUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(verify_admin_key),
):
    """
    PATCH /pools/{id}
    Admin-only (requires X-Admin-Key header).

    Fixes data-entry mistakes on a pool's supplier details or
    deadline — e.g. a malformed supplier_bank_code that only surfaced
    when Nomba's Transfer API rejected it at payout time. Deliberately
    does NOT allow changing target_amount, current_locked_amount, or
    status — see schemas/pool.py's PoolUpdate docstring for why.

    Only fields present in the request body are changed; anything
    omitted is left as-is.
    """
    try:
        pool_uuid = uuid.UUID(pool_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="pool_id must be a valid UUID")

    pool = db.query(Pool).filter(Pool.id == pool_uuid).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(pool, field, value)

    db.commit()
    db.refresh(pool)

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
        status=pool.status,
        deadline=pool.deadline,
        created_at=pool.created_at,
        fulfilled_at=pool.fulfilled_at,
        wholesaler_confirmed_at=pool.wholesaler_confirmed_at,
    )


@router.post("/{pool_id}/retry-payout", response_model=PoolRetryPayoutResponse)
def retry_payout(
    pool_id: str,
    db: Session = Depends(get_db),
    _admin: None = Depends(verify_admin_key),
):
    """
    POST /pools/{id}/retry-payout
    Admin-only (requires X-Admin-Key header).

    Manually forces an immediate retry of trigger_payout() for a pool
    that's fully funded but stuck at OPEN status — the same situation
    background/payout_finalizer.py already retries automatically every
    5 minutes (see that file's docstring for why a pool can get stuck
    here: trigger_payout's call to Nomba's Transfer API can raise
    AFTER the pool's current_locked_amount was already committed,
    leaving it fully funded but never actually paid out).

    This exists for exactly one situation: you've just fixed the
    underlying issue (e.g. Nomba Transfers API permissions, credential
    swap) and don't want to wait up to 5 minutes for the next
    scheduled retry — most likely to matter live, mid-demo.
    """
    try:
        pool_uuid = uuid.UUID(pool_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="pool_id must be a valid UUID")

    pool = db.query(Pool).filter(Pool.id == pool_uuid).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.status == PoolStatus.FULFILLED:
        return PoolRetryPayoutResponse(
            pool_id=str(pool.id),
            status=pool.status.value,
            pool_fulfilled=True,
            message="Pool is already fulfilled — nothing to retry.",
        )

    if pool.status not in (PoolStatus.OPEN, PoolStatus.PAYOUT_PROCESSING):
        raise HTTPException(
            status_code=400,
            detail=f"Pool is {pool.status.value} — payout cannot be retried in this state.",
        )

    if pool.status == PoolStatus.OPEN and Decimal(str(pool.current_locked_amount)) < Decimal(str(pool.target_amount)):
        raise HTTPException(
            status_code=400,
            detail="Pool has not reached its target amount yet — nothing to pay out.",
        )

    try:
        trigger_payout(db=db, pool=pool)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Payout retry failed: {e}",
        )

    db.refresh(pool)

    return PoolRetryPayoutResponse(
        pool_id=str(pool.id),
        status=pool.status.value,
        pool_fulfilled=pool.status == PoolStatus.FULFILLED,
        message=(
            "Payout confirmed and pool fulfilled."
            if pool.status == PoolStatus.FULFILLED
            else "Transfer accepted by Nomba, awaiting confirmation."
        ),
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
