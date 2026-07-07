"""
routers/esusu.py

Backend API for Ajo/Esusu rotating savings circles.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from models.identity import Identity, IdentityRole
from models.trader import Trader
from models.esusu import (
    EsusuCycle,
    EsusuMember,
    EsusuRound,
    EsusuContribution,
    EsusuStatus,
)
from schemas.esusu import (
    EsusuCycleCreate,
    EsusuContributeRequest,
    EsusuCycleResponse,
    EsusuListItem,
    EsusuJoinResponse,
    EsusuContributionResult,
    EsusuMemberResponse,
    EsusuRoundResponse,
    EsusuContributionResponse,
)
from services.auth import require_role
from services.esusu import (
    create_cycle as create_esusu_cycle,
    get_cycle,
    join_cycle as join_esusu_cycle,
    record_contribution,
    EsusuConflictError,
    EsusuNotFoundError,
    EsusuValidationError,
)

router = APIRouter()


def _trader_identity(identity: Identity) -> Trader:
    if identity.linked_trader_id is None:
        raise HTTPException(status_code=404, detail="This identity is not linked to a trader.")
    trader = identity.linked_trader
    if trader is None:
        raise HTTPException(status_code=404, detail="Linked trader record not found.")
    return trader


def _member_response(member: EsusuMember) -> EsusuMemberResponse:
    return EsusuMemberResponse(
        id=str(member.id),
        trader_id=str(member.trader_id),
        trader_name=member.trader.name if member.trader else "Unknown",
        trader_phone=member.trader.phone if member.trader else "",
        payout_position=member.payout_position,
        joined_at=member.joined_at,
        last_contributed_round=member.last_contributed_round,
        last_received_round=member.last_received_round,
    )


def _round_response(round_row: EsusuRound) -> EsusuRoundResponse:
    contribution_count = len(round_row.contributions)
    progress_pct = 0.0
    if float(round_row.target_amount) > 0:
        progress_pct = round((float(round_row.collected_amount) / float(round_row.target_amount)) * 100, 2)

    beneficiary_member = round_row.beneficiary_member
    return EsusuRoundResponse(
        id=str(round_row.id),
        round_number=round_row.round_number,
        beneficiary_member_id=str(round_row.beneficiary_member_id),
        beneficiary_trader_name=(beneficiary_member.trader.name if beneficiary_member and beneficiary_member.trader else "Unknown"),
        target_amount=float(round_row.target_amount),
        collected_amount=float(round_row.collected_amount),
        status=round_row.status.value,
        created_at=round_row.created_at,
        paid_at=round_row.paid_at,
        contribution_count=contribution_count,
        progress_pct=progress_pct,
    )


def _contribution_response(contribution: EsusuContribution) -> EsusuContributionResponse:
    return EsusuContributionResponse(
        id=str(contribution.id),
        round_id=str(contribution.round_id),
        trader_id=str(contribution.trader_id),
        trader_name=contribution.trader.name if contribution.trader else "Unknown",
        amount=float(contribution.amount),
        contributed_at=contribution.contributed_at,
    )


def _cycle_response(cycle: EsusuCycle) -> EsusuCycleResponse:
    members = [_member_response(member) for member in cycle.members]
    rounds = [_round_response(round_row) for round_row in cycle.rounds]
    contributions = [_contribution_response(contribution) for contribution in cycle.contributions]

    progress_pct = 0.0
    if cycle.total_members > 0:
        progress_pct = round((len(members) / cycle.total_members) * 100, 2)

    next_beneficiary_trader_name = None
    next_round = next((round_row for round_row in rounds if round_row.round_number == cycle.current_round_number), None)
    if next_round:
        next_beneficiary_trader_name = next_round.beneficiary_trader_name
    elif cycle.status == EsusuStatus.COMPLETED:
        next_beneficiary_trader_name = None

    return EsusuCycleResponse(
        id=str(cycle.id),
        title=cycle.title,
        description=cycle.description,
        market_name=cycle.market_name,
        contribution_amount=float(cycle.contribution_amount),
        total_members=cycle.total_members,
        frequency_days=cycle.frequency_days,
        current_round_number=cycle.current_round_number,
        status=cycle.status.value,
        total_collected=float(cycle.total_collected),
        created_at=cycle.created_at,
        activated_at=cycle.activated_at,
        completed_at=cycle.completed_at,
        members=members,
        rounds=rounds,
        contributions=contributions,
        progress_pct=progress_pct,
        next_beneficiary_trader_name=next_beneficiary_trader_name,
    )


@router.post("/cycles", response_model=EsusuCycleResponse, status_code=201)
def create_cycle(
    payload: EsusuCycleCreate,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_role(IdentityRole.TRADER)),
):
    trader = _trader_identity(identity)
    try:
        cycle = create_esusu_cycle(
            db=db,
            identity=identity,
            title=payload.title,
            market_name=payload.market_name,
            contribution_amount=payload.contribution_amount,
            total_members=payload.total_members,
            frequency_days=payload.frequency_days,
            description=payload.description,
        )
        cycle = get_cycle(db, cycle.id)
    except EsusuConflictError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except EsusuValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return _cycle_response(cycle)


@router.get("/cycles", response_model=list[EsusuListItem])
def list_cycles(db: Session = Depends(get_db)):
    cycles = db.query(EsusuCycle).order_by(EsusuCycle.created_at.desc()).all()
    return [
        EsusuListItem(
            id=str(cycle.id),
            title=cycle.title,
            market_name=cycle.market_name,
            contribution_amount=float(cycle.contribution_amount),
            total_members=cycle.total_members,
            current_round_number=cycle.current_round_number,
            status=cycle.status.value,
            progress_pct=round((len(cycle.members) / cycle.total_members) * 100, 2) if cycle.total_members else 0.0,
            created_at=cycle.created_at,
        )
        for cycle in cycles
    ]


@router.get("/cycles/{cycle_id}", response_model=EsusuCycleResponse)
def get_cycle_detail(cycle_id: str, db: Session = Depends(get_db)):
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="cycle_id must be a valid UUID")

    try:
        cycle = get_cycle(db, cycle_uuid)
    except EsusuNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return _cycle_response(cycle)


@router.post("/cycles/{cycle_id}/join", response_model=EsusuJoinResponse, status_code=201)
def join_cycle(
    cycle_id: str,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_role(IdentityRole.TRADER)),
):
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="cycle_id must be a valid UUID")

    try:
        cycle = get_cycle(db, cycle_uuid)
        member = join_esusu_cycle(db=db, identity=identity, cycle=cycle)
    except EsusuNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EsusuConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except EsusuValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    trader = _trader_identity(identity)
    status = cycle.status.value
    message = f"{trader.name} joined {cycle.title}"
    if cycle.status == EsusuStatus.ACTIVE:
        message = f"{cycle.title} is now active and ready to collect contributions."

    return EsusuJoinResponse(
        id=str(member.id),
        cycle_id=str(cycle.id),
        trader_id=str(trader.id),
        trader_name=trader.name,
        payout_position=member.payout_position,
        status=status,
        message=message,
    )


@router.post("/cycles/{cycle_id}/contribute", response_model=EsusuContributionResult)
def contribute(
    cycle_id: str,
    payload: EsusuContributeRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_role(IdentityRole.TRADER)),
):
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="cycle_id must be a valid UUID")

    try:
        cycle = get_cycle(db, cycle_uuid)
        result = record_contribution(
            db=db,
            identity=identity,
            cycle=cycle,
            nomba_transaction_ref=payload.nomba_transaction_ref,
        )
    except EsusuNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EsusuConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except EsusuValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return EsusuContributionResult(
        cycle_id=str(result["cycle"].id),
        round_number=result["round"].round_number,
        amount=result["amount"],
        round_paid=result["round_paid"],
        cycle_completed=result["cycle_completed"],
        next_round_number=result["next_round_number"],
        beneficiary_trader_name=result["beneficiary_trader_name"],
    )