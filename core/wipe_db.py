from core.database import SessionLocal

from models.pool import Pool
from models.payment import Payment
from models.pool_contribution import PoolContribution
from models.ledger_entry import LedgerEntry

REAL_POOL_ID = "f8708095-30d9-47d7-8db8-37d737cacb9f"

db = SessionLocal()

try:
    # Delete ledger entries for seed pools
    ledger_deleted = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.pool_id != REAL_POOL_ID)
        .delete(synchronize_session=False)
    )

    # Delete contributions for seed pools
    contributions_deleted = (
        db.query(PoolContribution)
        .filter(PoolContribution.pool_id != REAL_POOL_ID)
        .delete(synchronize_session=False)
    )

    # Delete payments for seed pools
    payments_deleted = (
        db.query(Payment)
        .filter(Payment.pool_id != REAL_POOL_ID)
        .delete(synchronize_session=False)
    )

    # Delete seed pools
    pools_deleted = (
        db.query(Pool)
        .filter(Pool.id != REAL_POOL_ID)
        .delete(synchronize_session=False)
    )

    db.commit()

    print("Ledger entries deleted:", ledger_deleted)
    print("Contributions deleted:", contributions_deleted)
    print("Payments deleted:", payments_deleted)
    print("Pools deleted:", pools_deleted)

except Exception as e:
    db.rollback()
    print("ERROR:", e)

finally:
    db.close()