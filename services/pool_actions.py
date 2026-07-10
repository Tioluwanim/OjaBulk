"""
services/pool_actions.py

Shared pool-join logic -- used by both POST /pools/{id}/join
(routers/pools.py) and the interactive USSD join-a-pool flow
(services/ussd.py), so there is exactly one implementation of "what
does it mean for a trader to join a pool" instead of two that could
drift apart.
"""

import uuid as uuid_module

from sqlalchemy.orm import Session

from models.pool import Pool, PoolStatus
from models.trader import Trader
from models.pool_contribution import PoolContribution, ContributionStatus


class PoolActionError(Exception):
    """Raised for any pool-join failure the caller should surface as
    a user-facing message."""
    pass


def join_pool_for_trader(db: Session, pool_id, trader_id) -> dict:
    """
    Joins `trader_id` to `pool_id` as an active contributor. Does NOT
    move money -- just sets this pool as a target for future
    payments/contribute-from-spendable calls, identical to
    routers/pools.py's POST /pools/{id}/join.

    Accepts either UUID objects or strings for both IDs.

    Returns a plain dict (not a schema) so callers on either side --
    a Pydantic response model for HTTP, or a plain-text USSD screen --
    can shape it however they need.

    Raises PoolActionError for anything the caller should show back
    to the trader (pool not open, wrong market, pool not found, etc).
    """
    if isinstance(pool_id, str):
        pool_id = uuid_module.UUID(pool_id)
    if isinstance(trader_id, str):
        trader_id = uuid_module.UUID(trader_id)

    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise PoolActionError("Pool not found.")
    if pool.status != PoolStatus.OPEN:
        raise PoolActionError(
            f"Pool is {pool.status.value} — cannot join a closed pool."
        )

    trader = db.query(Trader).filter(Trader.id == trader_id).first()
    if not trader:
        raise PoolActionError("Trader not found.")

    if pool.market_name and trader.market_name != pool.market_name:
        raise PoolActionError(
            f"This pool is for {pool.market_name}, but your trader "
            f"record belongs to {trader.market_name}."
        )

    existing = db.query(PoolContribution).filter(
        PoolContribution.trader_id == trader_id,
        PoolContribution.pool_id == pool_id,
        PoolContribution.status == ContributionStatus.LOCKED,
    ).first()
    if existing:
        return {
            "message": f"{trader.name} is already contributing to this pool",
            "trader_id": str(trader_id),
            "pool_id": str(pool_id),
            "pool_title": pool.title,
            "target": float(pool.target_amount),
            "already_joined": True,
        }

    contribution = PoolContribution(
        trader_id=trader_id,
        pool_id=pool_id,
        amount_locked=0,
        status=ContributionStatus.LOCKED,
    )
    db.add(contribution)
    db.commit()

    return {
        "message": f"{trader.name} joined {pool.title}",
        "trader_id": str(trader_id),
        "pool_id": str(pool_id),
        "pool_title": pool.title,
        "target": float(pool.target_amount),
        "already_joined": False,
    }
