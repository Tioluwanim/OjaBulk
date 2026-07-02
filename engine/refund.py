"""
engine/refund.py
"""

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session

from models.pool import Pool, PoolStatus
from models.pool_contribution import PoolContribution, ContributionStatus
from models.trader import Trader
from models.ledger_entry import LedgerEntry, EntryType
from services.sms import sms_service


def refund_pool(db: Session, pool: Pool) -> dict:
    pool.status = PoolStatus.REFUNDED
    db.flush()

    contributions: list[PoolContribution] = db.query(PoolContribution).filter(  # type: ignore
        PoolContribution.pool_id == pool.id,
        PoolContribution.status == ContributionStatus.LOCKED,
    ).all()

    total_refunded = Decimal("0")
    notified_traders = []

    for contribution in contributions:
        contribution.status = ContributionStatus.REFUNDED
        refund_amount = Decimal(str(contribution.amount_locked))

        if refund_amount <= Decimal("0"):
            continue

        total_refunded += refund_amount

        trader: Trader | None = db.query(Trader).filter(  # type: ignore
            Trader.id == contribution.trader_id
        ).first()

        if not trader:
            continue

        current_balance = Decimal(str(trader.spendable_balance))
        new_balance = current_balance + refund_amount
        trader.spendable_balance = new_balance

        db.add(LedgerEntry(
            trader_id=trader.id,
            pool_id=pool.id,
            entry_type=EntryType.POOL_REFUND,
            amount=refund_amount,
            balance_after=new_balance,
            note=f"Pool deadline missed — \u20a6{refund_amount:,.0f} refunded",
        ))

        notified_traders.append({
            "phone": trader.phone,
            "name": trader.name,
            "amount": refund_amount
        })

    db.commit()

    for t in notified_traders:
        try:
            sms_service.send_pool_refunded(
                phone=t["phone"],
                trader_name=t["name"],
                pool_title=pool.title,
                refund_amount=t["amount"],
            )
        except Exception as e:
            print(f"[Refund] SMS failed for {t['name']}: {e}")

    return {
        "pool_id": str(pool.id),
        "total_refunded": float(total_refunded),
        "contributors_count": len(contributions),
    }

def check_and_refund_expired_pools(db: Session) -> list[dict]:
    now = datetime.now(timezone.utc)
    expired_pools: list[Pool] = db.query(Pool).filter(  # type: ignore
        Pool.status == PoolStatus.OPEN,
        Pool.deadline < now,
    ).all()

    results = []
    for pool in expired_pools:
        try:
            result = refund_pool(db=db, pool=pool)
            results.append(result)
        except Exception as e:
            print(f"[Refund] Failed to refund pool {pool.id}: {e}")
    return results