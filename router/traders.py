"""
routers/traders.py

Trader registration and profile endpoints.
Now uses Pydantic schemas for request validation and response shaping.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from core.database import get_db
from models.trader import Trader
from models.ledger_entry import LedgerEntry
from services.virtual_accounts import virtual_account_service
from services.sms import sms_service
from schemas.trader import (
    TraderCreate,
    TraderResponse,
    TraderListItem,
    TraderLedgerResponse,
    LedgerEntryResponse,
)

router = APIRouter()


@router.post("", response_model=TraderResponse, status_code=201)
def register_trader(
    payload: TraderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    POST /traders
    Registers a new trader and provisions their Nomba virtual account.

    Pydantic validates and cleans the payload before this function runs —
    no manual field-presence checks needed anymore.
    """
    existing = db.query(Trader).filter(Trader.phone == payload.phone).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A trader with phone {payload.phone} already exists"
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
                entry_type=e.entry_type.value,
                amount=float(e.amount),
                balance_after=float(e.balance_after),
                note=e.note,
                pool_id=str(e.pool_id) if e.pool_id else None,
                created_at=e.created_at,
            )
            for e in entries
        ],
    )