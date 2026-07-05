"""
models/__init__.py

CRITICAL: This file must import every model, in this order, every time.

Why this file exists:
    SQLAlchemy relationships are declared as strings (e.g. relationship("Payment"))
    and resolved lazily when the mapper is first configured. If any model that
    participates in a relationship elsewhere hasn't been imported yet at that
    point, SQLAlchemy raises InvalidRequestError: failed to locate a name.

    Trader.py declares relationships to Payment, LedgerEntry, and PoolContribution.
    Pool.py declares relationships to PoolContribution, LedgerEntry, and Payment.
    If something imports `models.trader` alone (a script, a shell, a test,
    a future Alembic migration), those relationships fail to resolve unless
    every related model has already been imported into the same process.

    Importing `models` (this file) instead of individual model submodules
    guarantees every model is loaded together, in every context — not just
    in main.py, which only protects the running FastAPI app.
"""

from models.trader import Trader
from models.pool import Pool, PoolStatus
from models.pool_contribution import PoolContribution, ContributionStatus
from models.payment import Payment
from models.ledger_entry import LedgerEntry, EntryType
from models.identity import Identity, IdentityRole
from models.otp_session import OTPSession

__all__ = [
    "Trader",
    "Pool",
    "PoolStatus",
    "PoolContribution",
    "ContributionStatus",
    "Payment",
    "LedgerEntry",
    "EntryType",
    "Identity",
    "IdentityRole",
    "OTPSession",
]
