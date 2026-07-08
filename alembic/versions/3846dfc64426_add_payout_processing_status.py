"""add payout processing status

Revision ID: 3846dfc64426
Revises: 02f4bd748957
Create Date: 2026-07-07 10:39:20.595088

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3846dfc64426'
down_revision: Union[str, Sequence[str], None] = '02f4bd748957'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
