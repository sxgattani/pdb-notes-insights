"""add_soft_delete_and_full_sync_tracking

Revision ID: a7360a120ee5
Revises: 6312eb89fded
Create Date: 2026-01-26 04:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7360a120ee5'
down_revision: Union[str, None] = '6312eb89fded'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add deleted_at column to notes for soft deletes
    op.add_column('notes', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_notes_deleted_at'), 'notes', ['deleted_at'], unique=False)

    # Add is_full_sync and records_deleted columns to sync_history
    op.add_column('sync_history', sa.Column('is_full_sync', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('sync_history', sa.Column('records_deleted', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('sync_history', 'records_deleted')
    op.drop_column('sync_history', 'is_full_sync')
    op.drop_index(op.f('ix_notes_deleted_at'), table_name='notes')
    op.drop_column('notes', 'deleted_at')
