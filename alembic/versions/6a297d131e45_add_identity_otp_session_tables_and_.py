"""add identity and otp_session tables, pool auth columns

Revision ID: 6a297d131e45
Revises: c22080659485
Create Date: 2026-07-05 04:08:29.487664

This migration was generated via `alembic revision --autogenerate`
against the current models, then hand-cleaned: the raw autogenerate
output also included a large number of no-op `alter_column` UUID type
changes on traders/pools/payments/pool_contributions/ledger_entries.
Those were a SQLite-testing artifact (SQLite has no native UUID type,
so Alembic's SQLite comparator misreports every UUID column as if its
type had changed, even though nothing about those columns changed).
Confirmed these columns were always UUID in the real Postgres-facing
models — removed here so this migration only contains genuine changes.

Real changes in this migration:
    - New table: identities (trader/head_of_traders/wholesaler login)
    - New table: otp_sessions (short-lived login codes)
    - pools: new columns market_name, created_by_identity_id,
      wholesaler_confirmed_at
    - pools: new index on market_name
    - pools: new FK to identities(id) via created_by_identity_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a297d131e45'
down_revision: Union[str, Sequence[str], None] = 'c22080659485'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'otp_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'identities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column(
            'role',
            sa.Enum('TRADER', 'HEAD_OF_TRADERS', 'WHOLESALER', name='identityrole'),
            nullable=False,
        ),
        sa.Column('market_name', sa.String(), nullable=True),
        sa.Column('linked_trader_id', sa.UUID(), nullable=True),
        sa.Column('business_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(
            ['linked_trader_id'], ['traders.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone'),
    )
    op.create_index('idx_identity_market', 'identities', ['market_name'], unique=False)
    op.create_index('idx_identity_phone', 'identities', ['phone'], unique=False)
    op.create_index('idx_identity_role', 'identities', ['role'], unique=False)

    op.add_column('pools', sa.Column('market_name', sa.String(), nullable=True))
    op.add_column(
        'pools', sa.Column('created_by_identity_id', sa.UUID(), nullable=True)
    )
    op.add_column(
        'pools', sa.Column('wholesaler_confirmed_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('idx_pool_market', 'pools', ['market_name'], unique=False)

    # Batch mode: required for SQLite (which cannot ALTER a table to add
    # a foreign key constraint after creation — see SQLite dialect docs).
    # On Postgres this behaves identically to a plain create_foreign_key
    # call — batch mode is a no-op wrapper there, not a SQLite-only path
    # that changes behavior on the real target database.
    with op.batch_alter_table('pools') as batch_op:
        batch_op.create_foreign_key(
            'fk_pools_created_by_identity_id',
            'identities',
            ['created_by_identity_id'], ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('pools') as batch_op:
        batch_op.drop_constraint('fk_pools_created_by_identity_id', type_='foreignkey')
    op.drop_index('idx_pool_market', table_name='pools')
    op.drop_column('pools', 'wholesaler_confirmed_at')
    op.drop_column('pools', 'created_by_identity_id')
    op.drop_column('pools', 'market_name')

    op.drop_index('idx_identity_role', table_name='identities')
    op.drop_index('idx_identity_phone', table_name='identities')
    op.drop_index('idx_identity_market', table_name='identities')
    op.drop_table('identities')

    op.drop_table('otp_sessions')
