"""add_form_fields_to_notes

Revision ID: e1a2b3c4d5e6
Revises: a7360a120ee5
Create Date: 2026-03-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, None] = 'a7360a120ee5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notes', sa.Column('opportunity_type', sa.String(), nullable=True))
    op.create_index(op.f('ix_notes_opportunity_type'), 'notes', ['opportunity_type'], unique=False)

    op.add_column('notes', sa.Column('product_area', sa.String(), nullable=True))
    op.create_index(op.f('ix_notes_product_area'), 'notes', ['product_area'], unique=False)

    op.add_column('notes', sa.Column('customer_impact', sa.String(), nullable=True))
    op.create_index(op.f('ix_notes_customer_impact'), 'notes', ['customer_impact'], unique=False)

    op.add_column('notes', sa.Column('functionality_timeline', sa.String(), nullable=True))
    op.create_index(op.f('ix_notes_functionality_timeline'), 'notes', ['functionality_timeline'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notes_functionality_timeline'), table_name='notes')
    op.drop_column('notes', 'functionality_timeline')

    op.drop_index(op.f('ix_notes_customer_impact'), table_name='notes')
    op.drop_column('notes', 'customer_impact')

    op.drop_index(op.f('ix_notes_product_area'), table_name='notes')
    op.drop_column('notes', 'product_area')

    op.drop_index(op.f('ix_notes_opportunity_type'), table_name='notes')
    op.drop_column('notes', 'opportunity_type')
