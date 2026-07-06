"""
services/esusu.py

Minimal rotating savings logic for Ajo/Esusu cycles.
The feature is intentionally isolated from the pool engine so it can
grow independently without changing the settlement logic already used
for wholesale pools.
"""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.identity import Identity, IdentityRole
from models.trader import Trader
from models.esusu import (
    EsusuCycle,
    EsusuMember,
    EsusuRound,
    EsusuContribution,
    EsusuStatus,
    EsusuRoundStatus,
)


class EsusuError(Exception):
    pass


class EsusuNotFoundError(EsusuError):
    pass


class EsusuConflictError(EsusuError):
    pass


class EsusuValidationError(EsusuError):
    pass


def _assert_trader_identity(identity: Identity) -> Trader:
    if identity.role != IdentityRole.TRADER:
        raise EsusuConflictError("Only trader identities can use Ajo/Esusu cycles.")
    if identity.linked_trader_id is None:
        raise EsusuValidationError("This trader identity is not linked to a trader record.")
    return identity.linked_trader


def create_cycle(db: Session, identity: Identity, title: str, market_name: str,
                 contribution_amount: float, total_members: int,
                 frequency_days: int = 7, description: str | None = None) -> EsusuCycle:
    trader = _assert_trader_identity(identity)

    if trader.market_name != market_name:
        raise EsusuConflictError(
            f"You are registered in {trader.market_name}, not {market_name}."
        )

    cycle = EsusuCycle(
        title=title,
        description=description,
        market_name=market_name,
        contribution_amount=contribution_amount,
        total_members=total_members,
        frequency_days=frequency_days,
        created_by_identity_id=identity.id,
        status=EsusuStatus.OPEN,
        current_round_number=1,
        total_collected=0,
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


def get_cycle(db: Session, cycle_id) -> EsusuCycle:
    cycle = db.query(EsusuCycle).filter(EsusuCycle.id == cycle_id).first()
    if not cycle:
        raise EsusuNotFoundError("Esusu cycle not found.")
    return cycle


def join_cycle(db: Session, identity: Identity, cycle: EsusuCycle) -> EsusuMember:
    trader = _assert_trader_identity(identity)

    if cycle.status != EsusuStatus.OPEN:
        raise EsusuConflictError(f"This cycle is {cycle.status.value} and can no longer accept members.")

    if cycle.market_name and trader.market_name != cycle.market_name:
        raise EsusuConflictError(
            f"This cycle is for {cycle.market_name}, but your trader record belongs to {trader.market_name}."
        )

    existing = db.query(EsusuMember).filter(
        EsusuMember.cycle_id == cycle.id,
        EsusuMember.trader_id == trader.id,
    ).first()
    if existing:
        raise EsusuConflictError("You are already a member of this cycle.")

    member_count = db.query(func.count(EsusuMember.id)).filter(
        EsusuMember.cycle_id == cycle.id,
    ).scalar() or 0

    if member_count >= cycle.total_members:
        raise EsusuConflictError("This cycle already has all required members.")

    member = EsusuMember(
        cycle_id=cycle.id,
        trader_id=trader.id,
        payout_position=member_count + 1,
    )
    db.add(member)
    db.flush()

    if member_count + 1 == cycle.total_members:
        cycle.status = EsusuStatus.ACTIVE
        cycle.activated_at = datetime.now(timezone.utc)
        cycle.current_round_number = 1
        _ensure_round(db, cycle, 1)

    db.commit()
    db.refresh(member)
    return member


def _ensure_round(db: Session, cycle: EsusuCycle, round_number: int) -> EsusuRound:
    existing_round = db.query(EsusuRound).filter(
        EsusuRound.cycle_id == cycle.id,
        EsusuRound.round_number == round_number,
    ).first()
    if existing_round:
        return existing_round

    beneficiary = db.query(EsusuMember).filter(
        EsusuMember.cycle_id == cycle.id,
        EsusuMember.payout_position == round_number,
    ).first()
    if not beneficiary:
        raise EsusuValidationError("No beneficiary is assigned for the requested round.")

    round_row = EsusuRound(
        cycle_id=cycle.id,
        round_number=round_number,
        beneficiary_member_id=beneficiary.id,
        target_amount=float(cycle.contribution_amount) * cycle.total_members,
        collected_amount=0,
        status=EsusuRoundStatus.OPEN,
    )
    db.add(round_row)
    db.flush()
    return round_row


def record_contribution(db: Session, identity: Identity, cycle: EsusuCycle) -> dict:
    trader = _assert_trader_identity(identity)

    if cycle.status != EsusuStatus.ACTIVE:
        raise EsusuConflictError(f"This cycle is {cycle.status.value} and is not collecting contributions.")

    member = db.query(EsusuMember).filter(
        EsusuMember.cycle_id == cycle.id,
        EsusuMember.trader_id == trader.id,
    ).first()
    if not member:
        raise EsusuConflictError("You must join the cycle before contributing.")

    round_row = _ensure_round(db, cycle, cycle.current_round_number)

    existing = db.query(EsusuContribution).filter(
        EsusuContribution.round_id == round_row.id,
        EsusuContribution.trader_id == trader.id,
    ).first()
    if existing:
        raise EsusuConflictError("You have already contributed to this round.")

    amount = float(cycle.contribution_amount)
    contribution = EsusuContribution(
        cycle_id=cycle.id,
        round_id=round_row.id,
        trader_id=trader.id,
        amount=amount,
    )
    db.add(contribution)

    round_row.collected_amount = float(round_row.collected_amount) + amount
    cycle.total_collected = float(cycle.total_collected) + amount
    member.last_contributed_round = cycle.current_round_number

    round_paid = False
    next_round_number = None

    if float(round_row.collected_amount) >= float(round_row.target_amount):
        round_row.status = EsusuRoundStatus.PAID
        round_row.paid_at = datetime.now(timezone.utc)
        beneficiary = round_row.beneficiary_member
        if beneficiary:
            beneficiary.last_received_round = round_row.round_number

        cycle.current_round_number += 1
        round_paid = True

        if cycle.current_round_number > cycle.total_members:
            cycle.status = EsusuStatus.COMPLETED
            cycle.completed_at = datetime.now(timezone.utc)
        else:
            next_round_number = cycle.current_round_number
            _ensure_round(db, cycle, cycle.current_round_number)

    db.commit()

    beneficiary_member = round_row.beneficiary_member
    beneficiary_trader_name = beneficiary_member.trader.name if beneficiary_member and beneficiary_member.trader else "Unknown"

    return {
        "cycle": cycle,
        "round": round_row,
        "amount": amount,
        "round_paid": round_paid,
        "cycle_completed": cycle.status == EsusuStatus.COMPLETED,
        "next_round_number": next_round_number,
        "beneficiary_trader_name": beneficiary_trader_name,
    }