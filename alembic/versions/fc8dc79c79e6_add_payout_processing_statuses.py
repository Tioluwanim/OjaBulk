"""add payout processing statuses

Revision ID: fc8dc79c79e6
Revises: 3846dfc64426
Create Date: 2026-07-07 10:51:41.876394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc8dc79c79e6'
down_revision: Union[str, Sequence[str], None] = '3846dfc64426'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute(
        "ALTER TYPE poolstatus ADD VALUE IF NOT EXISTS 'PAYOUT_PROCESSING';"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
