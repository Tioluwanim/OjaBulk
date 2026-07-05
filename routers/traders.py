"""
routers/traders.py

Trader registration and profile endpoints.
Now uses Pydantic schemas for request validation and response shaping.

TWO DIFFERENT ACCESS PATTERNS IN THIS FILE, ON PURPOSE:

    GET /traders/{id} and GET /traders/{id}/ledger
        No auth required — this is the ADMIN / Head of Traders view,
        used from the dashboard to look up any trader by UUID. Not
        scoped to "your own" data; scoped by knowing the UUID at all,
        which in practice means "someone with dashboard access."

    GET /me and GET /me/pools
        REQUIRES a valid trader session token. Always resolves to the
        CALLING trader's own linked_trader_id from their verified
        Identity — never accepts a trader_id from the client. This is
        what closes the real gap: before this, a trader had no way to
        see their own balance without someone else handing them their
        raw UUID, and there was no enforcement that a trader couldn't
        just guess or share UUIDs to view others' balances via /me
        (impossible now, since /me only ever resolves to yourself).
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from core.database import get_db
from models.trader import Trader
from models.ledger_entry import LedgerEntry
from models.pool_contribution import PoolContribution
from models.pool import Pool, PoolStatus
from models.identity import Identity, IdentityRole
from services.virtual_accounts import virtual_account_service
from services.auth import require_role
from services.sms import sms_service
from schemas.trader import (
    TraderCreate,
    TraderResponse,
    TraderListItem,
    TraderLedgerResponse,
    LedgerEntryResponse,
)
from schemas.pool import PoolResponse

router = APIRouter()


@router.post("", response_model=TraderResponse, status_code=201)
def register_trader(
    payload: TraderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    POST /traders
    Registers a new trader, provisions their Nomba virtual account,
    AND creates a linked Identity row so they can log in via OTP.

    Trader.phone and Identity.phone are always kept identical — the
    trader logs in with the same number they registered with. If an
    Identity with this phone somehow already exists (e.g. registered
    as head_of_traders or wholesaler on the same number — an edge
    case, but a real one worth guarding against), registration fails
    loudly rather than silently overwriting someone's role.
    """
    existing = db.query(Trader).filter(Trader.phone == payload.phone).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A trader with phone {payload.phone} already exists"
        )

    existing_identity = db.query(Identity).filter(
        Identity.phone == payload.phone
    ).first()
    if existing_identity:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This phone number is already registered as "
                f"{existing_identity.role.value}. A phone number can "
                f"only be linked to one role."
            )
        )

    trader = Trader(
        name=payload.name,
        phone=payload.phone,
        stall_number=payload.stall_number,
        market_name=payload.market_name,
    )
    db.add(trader)
    db.flush()   # Get the UUID before calling Nomba

    try:
        account = virtual_account_service.create(
            trader_id=str(trader.id),
            trader_name=payload.name,
        )
        trader.virtual_account_number = account["bank_account_number"]
        trader.bank_name              = account["bank_name"]
        trader.bank_account_name      = account["bank_account_name"]
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"Virtual account provisioning failed: {str(e)}"
        )

    # Create the linked Identity so this trader can log in via OTP
    # and see their own balance/pools. This is a separate row from
    # Trader on purpose — see models/identity.py's module docstring.
    identity = Identity(
        phone=payload.phone,
        display_name=payload.name,
        role=IdentityRole.TRADER,
        market_name=payload.market_name,
        linked_trader_id=trader.id,
    )
    db.add(identity)

    db.commit()
    db.refresh(trader)

    background_tasks.add_task(
        sms_service.send_account_created,
        phone=trader.phone,
        trader_name=trader.name,
        account_number=trader.virtual_account_number,
        bank_name=trader.bank_name or "",
    )

    return TraderResponse(
        id=str(trader.id),
        name=trader.name,
        phone=trader.phone,
        stall_number=trader.stall_number,
        market_name=trader.market_name,
        virtual_account_number=trader.virtual_account_number,
        bank_name=trader.bank_name,
        bank_account_name=trader.bank_account_name,
        spendable_balance=float(trader.spendable_balance),
        total_contributed=float(trader.total_contributed),
        created_at=trader.created_at,
    )


@router.get("", response_model=list[TraderListItem])
def list_traders(db: Session = Depends(get_db)):
    """GET /traders — list all traders with balances"""
    traders = db.query(Trader).order_by(Trader.created_at.desc()).all()
    return [
        TraderListItem(
            id=str(t.id),
            name=t.name,
            phone=t.phone,
            stall_number=t.stall_number,
            market_name=t.market_name,
            virtual_account_number=t.virtual_account_number,
            bank_name=t.bank_name,
            spendable_balance=float(t.spendable_balance),
            total_contributed=float(t.total_contributed),
        )
        for t in traders
    ]


@router.get("/me", response_model=TraderResponse)
def get_my_profile(
    identity: Identity = Depends(require_role(IdentityRole.TRADER)),
    db: Session = Depends(get_db),
):
    """
    GET /traders/me

    Returns the LOGGED-IN trader's own profile and balance. Never
    accepts a trader_id — always resolves via identity.linked_trader_id
    from the verified session token. This is the endpoint a trader's
    phone app calls after login to show "your balance."

    IMPORTANT — route ordering: this must be declared BEFORE
    GET /{trader_id} below. FastAPI matches routes in the order they
    are declared, and /{trader_id} is a path parameter that would
    otherwise greedily match the literal string "me" as if it were a
    trader UUID, causing a 422 (invalid UUID) instead of ever reaching
    this handler.
    """
    if identity.linked_trader_id is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "This identity has no linked trader record. "
                "This should not happen for role=trader — contact support."
            )
        )

    trader = db.query(Trader).filter(
        Trader.id == identity.linked_trader_id
    ).first()

    if not trader:
        raise HTTPException(
            status_code=404,
            detail="Linked trader record not found."
        )

    return TraderResponse(
        id=str(trader.id),
        name=trader.name,
        phone=trader.phone,
        stall_number=trader.stall_number,
        market_name=trader.market_name,
        virtual_account_number=trader.virtual_account_number,
        bank_name=trader.bank_name,
        bank_account_name=trader.bank_account_name,
        spendable_balance=float(trader.spendable_balance),
        total_contributed=float(trader.total_contributed),
        created_at=trader.created_at,
    )


@router.get("/me/ledger", response_model=TraderLedgerResponse)
def get_my_ledger(
    identity: Identity = Depends(require_role(IdentityRole.TRADER)),
    db: Session = Depends(get_db),
):
    """
    GET /traders/me/ledger

    Same self-service pattern as GET /me — the logged-in trader's own
    full ledger history, never accepting a trader_id from the client.
    """
    if identity.linked_trader_id is None:
        raise HTTPException(status_code=404, detail="No linked trader record.")

    trader = db.query(Trader).filter(
        Trader.id == identity.linked_trader_id
    ).first()
    if not trader:
        raise HTTPException(status_code=404, detail="Linked trader record not found.")

    entries = db.query(LedgerEntry).filter(
        LedgerEntry.trader_id == trader.id
    ).order_by(LedgerEntry.created_at.desc()).all()

    return TraderLedgerResponse(
        trader_id=str(trader.id),
        trader_name=trader.name,
        current_spendable=float(trader.spendable_balance),
        entries=[
            LedgerEntryResponse(
                id=str(e.id),
                entry_type=str(e.entry_type.value),
                amount=float(e.amount),
                balance_after=float(e.balance_after),
                note=e.note,
                pool_id=str(e.pool_id) if e.pool_id else None,
                created_at=e.created_at,
            )
            for e in entries
        ],
    )


@router.get("/me/pools", response_model=list[PoolResponse])
def get_my_pools(
    identity: Identity = Depends(require_role(IdentityRole.TRADER)),
    db: Session = Depends(get_db),
):
    """
    GET /traders/me/pools

    Returns every pool the logged-in trader has EVER contributed to
    (any ContributionStatus — locked, released, or refunded), not just
    currently-open ones. A trader should be able to see the pool they
    were refunded from just as easily as one they're actively
    contributing to — history matters here, not just active state.
    """
    if identity.linked_trader_id is None:
        raise HTTPException(status_code=404, detail="No linked trader record.")

    pools = (
        db.query(Pool)
        .join(PoolContribution, PoolContribution.pool_id == Pool.id)
        .filter(PoolContribution.trader_id == identity.linked_trader_id)
        .order_by(Pool.created_at.desc())
        .all()
    )

    return [_pool_response_for_trader(p) for p in pools]


def _pool_response_for_trader(pool: Pool) -> PoolResponse:
    """
    Local helper — mirrors routers/pools.py's _pool_response, kept as
    its own copy rather than importing across router modules (importing
    router internals from another router is a smell; if this needs to
    be shared later, it belongs in a shared schemas/pool.py helper, not
    imported router-to-router).
    """
    progress_pct = 0.0
    if pool.target_amount and float(pool.target_amount) > 0:
        progress_pct = round(
            (float(pool.current_locked_amount) / float(pool.target_amount)) * 100, 2
        )

    return PoolResponse(
        id=str(pool.id),
        title=pool.title,
        market_name=pool.market_name,
        target_amount=float(pool.target_amount),
        current_locked_amount=float(pool.current_locked_amount),
        progress_pct=progress_pct,
        supplier_name=pool.supplier_name,
        supplier_account_number=pool.supplier_account_number,
        supplier_bank_code=pool.supplier_bank_code,
        status=str(pool.status.value),
        deadline=pool.deadline,
        created_at=pool.created_at,
        fulfilled_at=pool.fulfilled_at,
        wholesaler_confirmed_at=pool.wholesaler_confirmed_at,
    )


@router.get("/{trader_id}", response_model=TraderResponse)
def get_trader(trader_id: str, db: Session = Depends(get_db)):
    """GET /traders/{id} — single trader profile"""
    try:
        trader_uuid = uuid.UUID(trader_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="trader_id must be a valid UUID")

    trader = db.query(Trader).filter(Trader.id == trader_uuid).first()
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    return TraderResponse(
        id=str(trader.id),
        name=trader.name,
        phone=trader.phone,
        stall_number=trader.stall_number,
        market_name=trader.market_name,
        virtual_account_number=trader.virtual_account_number,
        bank_name=trader.bank_name,
        bank_account_name=trader.bank_account_name,
        spendable_balance=float(trader.spendable_balance),
        total_contributed=float(trader.total_contributed),
        created_at=trader.created_at,
    )


@router.get("/{trader_id}/ledger", response_model=TraderLedgerResponse)
def get_trader_ledger(trader_id: str, db: Session = Depends(get_db)):
    """GET /traders/{id}/ledger — full immutable ledger history"""
    try:
        trader_uuid = uuid.UUID(trader_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="trader_id must be a valid UUID")

    trader = db.query(Trader).filter(Trader.id == trader_uuid).first()
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    entries = db.query(LedgerEntry).filter(
        LedgerEntry.trader_id == trader_uuid
    ).order_by(LedgerEntry.created_at.desc()).all()

    return TraderLedgerResponse(
        trader_id=trader_id,
        trader_name=trader.name,
        current_spendable=float(trader.spendable_balance),
        entries=[
            LedgerEntryResponse(
                id=str(e.id),
                entry_type=str(e.entry_type.value),
                amount=float(e.amount),
                balance_after=float(e.balance_after),
                note=e.note,
                pool_id=str(e.pool_id) if e.pool_id else None,
                created_at=e.created_at,
            )
            for e in entries
        ],
    )
