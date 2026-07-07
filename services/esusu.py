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

from decimal import Decimal

from models.identity import Identity, IdentityRole
from models.trader import Trader
from models.payment import Payment
from models.ledger_entry import LedgerEntry, EntryType
from models.esusu import (
    EsusuCycle,
    EsusuMember,
    EsusuRound,
    EsusuContribution,
    EsusuStatus,
    EsusuRoundStatus,
)
from services.sms import sms_service


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


def record_contribution(
    db: Session,
    identity: Identity,
    cycle: EsusuCycle,
    nomba_transaction_ref: str,
) -> dict:
    """
    FIX: this used to be pure self-attestation — a trader could hit
    POST /cycles/{id}/contribute with no request body at all, and the
    system just believed them. Now the caller must supply the
    nomba_transaction_ref of a real inbound payment, and this function
    verifies it against the Payment row that engine/reconciliation.py
    already created from a genuine, HMAC-verified Nomba
    payment_success webhook — the exact same source of truth the Pool
    system relies on. No Payment row, no contribution.
    """
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

    # --------------------------------------------------
    # Verify the real, webhook-confirmed payment
    # --------------------------------------------------

    payment = db.query(Payment).filter(
        Payment.nomba_transaction_ref == nomba_transaction_ref,
    ).first()

    if not payment:
        raise EsusuValidationError(
            "No confirmed payment found for that reference. "
            "Send the contribution amount to your OjaBulk virtual "
            "account first, then try again once it's confirmed."
        )

    if payment.trader_id != trader.id:
        raise EsusuValidationError(
            "That payment reference does not belong to your account."
        )

    already_used = db.query(EsusuContribution).filter(
        EsusuContribution.payment_id == payment.id,
    ).first()
    if already_used:
        raise EsusuConflictError(
            "That payment has already been used for a contribution."
        )

    amount = float(cycle.contribution_amount)

    if float(payment.amount_received) < amount:
        raise EsusuValidationError(
            f"That payment (\u20a6{float(payment.amount_received):,.0f}) is "
            f"less than the required contribution of \u20a6{amount:,.0f}."
        )

    # --------------------------------------------------
    # Record the contribution against the verified payment
    # --------------------------------------------------

    contribution = EsusuContribution(
        cycle_id=cycle.id,
        round_id=round_row.id,
        trader_id=trader.id,
        payment_id=payment.id,
        amount=amount,
    )
    db.add(contribution)
    db.flush()

    new_balance = Decimal(str(trader.spendable_balance))
    db.add(
        LedgerEntry(
            trader_id=trader.id,
            pool_id=None,
            entry_type=EntryType.ESUSU_CONTRIBUTION,
            amount=amount,
            balance_after=float(new_balance),
            note=(
                f"Esusu contribution of \u20a6{amount:,.0f} to "
                f"{cycle.title}, round {round_row.round_number}. "
                f"Verified against payment {nomba_transaction_ref}."
            ),
        )
    )

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
            _credit_beneficiary(db, round_row, beneficiary)

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


def _credit_beneficiary(db: Session, round_row: EsusuRound, beneficiary: EsusuMember) -> None:
    """
    Every contribution feeding this round is already backed by a
    real, webhook-verified Payment (see record_contribution above),
    so round_row.collected_amount represents genuinely-received naira
    sitting in OjaBulk's Nomba sub-account, not simulated numbers.

    Two payout paths, depending on what the beneficiary has on file:

    1. Trader HAS payout_bank_code + payout_account_number set:
       a real Nomba transfer is sent straight to their own bank
       account -- the same Transfer API and sub-account
       engine/payout.py already uses for Pool supplier payouts, via
       services/transfers.py's send_to_trader(). This mirrors
       engine/payout.py's pending-transfer handling exactly: if Nomba
       accepts but hasn't confirmed (is_pending=True), the round is
       held at PAYOUT_PROCESSING and the beneficiary gets a
       "processing" SMS, not a "confirmed" one, until
       background/esusu_payout_finalizer.py requeries and confirms.

    2. Trader has NO payout bank details on file: falls back to
       crediting their in-app spendable_balance directly (the
       original fix) -- still real, ledger-backed money, just an
       internal wallet credit rather than an external bank transfer,
       since there's nowhere else to send it yet.
    """
    trader = beneficiary.trader
    if trader is None:
        print(f"[Esusu] Beneficiary member {beneficiary.id} has no linked trader — cannot credit.")
        return

    amount = Decimal(str(round_row.collected_amount))

    has_payout_bank_details = bool(
        trader.payout_bank_code and trader.payout_account_number
    )

    if has_payout_bank_details:
        _credit_beneficiary_via_bank_transfer(db, round_row, trader, amount)
    else:
        _credit_beneficiary_via_wallet(db, round_row, trader, amount)


def _credit_beneficiary_via_bank_transfer(
    db: Session,
    round_row: EsusuRound,
    trader: Trader,
    amount: Decimal,
) -> None:
    from services.transfers import transfer_service

    cycle = round_row.cycle

    try:
        transfer_result = transfer_service.send_to_trader(
            round_id=str(round_row.id),
            cycle_title=cycle.title if cycle else "Esusu",
            amount=float(amount),
            trader_account_number=trader.payout_account_number,
            trader_bank_code=trader.payout_bank_code,
            trader_account_name=(
                trader.payout_account_name or trader.name
            ),
        )
    except Exception as e:
        # Do NOT silently fall back to a wallet credit here -- that
        # would risk crediting twice if the transfer actually went
        # through despite the exception (e.g. a timeout after Nomba
        # accepted it). Flag loudly for manual review instead.
        print(
            f"[Esusu] ALERT: bank transfer failed for round {round_row.id} "
            f"(trader {trader.id}): {e}. Round left OPEN/PAID-pending "
            f"payout -- manual review required, do NOT re-trigger "
            f"automatically."
        )
        round_row.nomba_transfer_ref = None
        db.flush()
        return

    round_row.nomba_transfer_ref = transfer_result.get("transfer_ref")

    if transfer_result.get("is_pending"):
        round_row.status = EsusuRoundStatus.PAYOUT_PROCESSING
        db.flush()

        try:
            sms_service.send_esusu_payout_processing(
                phone=trader.phone,
                trader_name=trader.name,
                amount=float(amount),
                round_number=round_row.round_number,
            )
        except Exception as e:
            print(f"[Esusu] Processing SMS failed for trader {trader.id}: {e}")
        return

    # Confirmed synchronously -- finalize immediately.
    _finalize_bank_transfer_payout(db, round_row, trader, amount)


def _finalize_bank_transfer_payout(
    db: Session,
    round_row: EsusuRound,
    trader: Trader,
    amount: Decimal,
) -> None:
    """
    Records the ledger entry once a real bank transfer to the
    beneficiary is confirmed. Deliberately does NOT touch
    trader.spendable_balance -- the money left the Nomba sub-account
    for the trader's own external bank account, it never sat in their
    in-app wallet, so crediting spendable_balance here would be
    recording money that was never actually there.
    """
    round_row.status = EsusuRoundStatus.PAID
    round_row.paid_at = datetime.now(timezone.utc)

    db.add(
        LedgerEntry(
            trader_id=trader.id,
            pool_id=None,
            entry_type=EntryType.ESUSU_PAYOUT,
            amount=float(amount),
            balance_after=float(trader.spendable_balance),
            note=(
                f"Esusu payout: \u20a6{amount:,.0f} transferred directly "
                f"to beneficiary's bank account for round "
                f"{round_row.round_number} of cycle {round_row.cycle_id}. "
                f"transfer_ref={round_row.nomba_transfer_ref}"
            ),
        )
    )
    db.flush()

    try:
        sms_service.send_esusu_payout(
            phone=trader.phone,
            trader_name=trader.name,
            amount=float(amount),
            round_number=round_row.round_number,
        )
    except Exception as e:
        print(f"[Esusu] Payout SMS failed for trader {trader.id}: {e}")


def finalize_pending_esusu_payout(db: Session, round_row: EsusuRound) -> dict:
    """
    Called by background/esusu_payout_finalizer.py for any round sitting
    in PAYOUT_PROCESSING. Mirrors engine/payout.py's
    finalize_pending_payout() for Pool payouts.
    """
    from services.transfers import transfer_service

    if not round_row.nomba_transfer_ref:
        print(f"[EsusuPayoutFinalizer] Round {round_row.id} has no transfer_ref — skipping.")
        return {"round_id": str(round_row.id), "action": "skipped_no_ref"}

    beneficiary = round_row.beneficiary_member
    trader = beneficiary.trader if beneficiary else None
    if trader is None:
        print(f"[EsusuPayoutFinalizer] Round {round_row.id} has no beneficiary trader — skipping.")
        return {"round_id": str(round_row.id), "action": "skipped_no_trader"}

    try:
        result = transfer_service.requery_transfer(round_row.nomba_transfer_ref)
    except Exception as e:
        print(f"[EsusuPayoutFinalizer] Requery failed for round {round_row.id}: {e}")
        return {"round_id": str(round_row.id), "action": "requery_failed"}

    status = str(result.get("status", "")).upper()
    amount = Decimal(str(round_row.collected_amount))

    if status in ("SUCCESS", "SUCCESSFUL", "COMPLETED"):
        _finalize_bank_transfer_payout(db, round_row, trader, amount)
        db.commit()
        print(f"[EsusuPayoutFinalizer] Round {round_row.id} confirmed and finalized.")
        return {"round_id": str(round_row.id), "action": "finalized"}

    if status in ("FAILED", "REVERSED", "DECLINED", "REFUND"):
        print(
            f"[EsusuPayoutFinalizer] ALERT: transfer for round {round_row.id} "
            f"came back '{status}'. Manual review required — do not treat "
            f"as paid. If retrying, you MUST use a new merchantTxRef; the "
            f"original ({round_row.nomba_transfer_ref}) is terminal per "
            f"Nomba's docs."
        )
        return {"round_id": str(round_row.id), "action": "failed_needs_review", "status": status}

    print(f"[EsusuPayoutFinalizer] Round {round_row.id} still '{status}' — will recheck.")
    return {"round_id": str(round_row.id), "action": "still_pending", "status": status}


def _credit_beneficiary_via_wallet(
    db: Session,
    round_row: EsusuRound,
    trader: Trader,
    amount: Decimal,
) -> None:
    """
    Fallback used when the beneficiary has no payout bank details on
    file: credits their in-app spendable_balance directly instead of
    an external bank transfer. Still real, ledger-backed money — just
    an internal wallet credit rather than money leaving the sub-account.
    """
    new_balance = Decimal(str(trader.spendable_balance)) + amount
    trader.spendable_balance = float(new_balance)

    round_row.status = EsusuRoundStatus.PAID
    round_row.paid_at = datetime.now(timezone.utc)

    db.add(
        LedgerEntry(
            trader_id=trader.id,
            pool_id=None,
            entry_type=EntryType.ESUSU_PAYOUT,
            amount=float(amount),
            balance_after=float(new_balance),
            note=(
                f"Esusu payout: \u20a6{amount:,.0f} credited to in-app "
                f"wallet as beneficiary for round {round_row.round_number} "
                f"of cycle {round_row.cycle_id} (no payout bank details "
                f"on file)."
            ),
        )
    )

    db.flush()

    try:
        sms_service.send_esusu_payout(
            phone=trader.phone,
            trader_name=trader.name,
            amount=float(amount),
            round_number=round_row.round_number,
        )
    except Exception as e:
        print(f"[Esusu] Payout SMS failed for trader {trader.id}: {e}")
