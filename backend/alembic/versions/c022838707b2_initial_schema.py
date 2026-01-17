"""initial schema

Revision ID: c022838707b2
Revises:
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c022838707b2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pb_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_pb_id'), 'users', ['pb_id'], unique=True)

    # Create teams table
    op.create_table('teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pb_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teams_id'), 'teams', ['id'], unique=False)
    op.create_index(op.f('ix_teams_pb_id'), 'teams', ['pb_id'], unique=True)

    # Create companies table
    op.create_table('companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pb_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('customer_id', sa.String(), nullable=True),
        sa.Column('account_sales_theatre', sa.String(), nullable=True),
        sa.Column('cse', sa.String(), nullable=True),
        sa.Column('arr', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('account_type', sa.String(), nullable=True),
        sa.Column('contract_start_date', sa.Date(), nullable=True),
        sa.Column('contract_end_date', sa.Date(), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)
    op.create_index(op.f('ix_companies_pb_id'), 'companies', ['pb_id'], unique=True)
    op.create_index(op.f('ix_companies_account_sales_theatre'), 'companies', ['account_sales_theatre'], unique=False)

    # Create customers table
    op.create_table('customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pb_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_id'), 'customers', ['id'], unique=False)
    op.create_index(op.f('ix_customers_pb_id'), 'customers', ['pb_id'], unique=True)
    op.create_index(op.f('ix_customers_company_id'), 'customers', ['company_id'], unique=False)

    # Create components table
    op.create_table('components',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pb_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['components.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_components_id'), 'components', ['id'], unique=False)
    op.create_index(op.f('ix_components_pb_id'), 'components', ['pb_id'], unique=True)
    op.create_index(op.f('ix_components_parent_id'), 'components', ['parent_id'], unique=False)

    # Create features table
    op.create_table('features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pb_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('component_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('creator_id', sa.Integer(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('product_area', sa.String(), nullable=True),
        sa.Column('product_area_stack_rank', sa.Integer(), nullable=True),
        sa.Column('committed', sa.Boolean(), nullable=True),
        sa.Column('risk', sa.String(), nullable=True),
        sa.Column('tech_lead_id', sa.Integer(), nullable=True),
        sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['component_id'], ['components.id'], ),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['tech_lead_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_features_id'), 'features', ['id'], unique=False)
    op.create_index(op.f('ix_features_pb_id'), 'features', ['pb_id'], unique=True)
    op.create_index(op.f('ix_features_component_id'), 'features', ['component_id'], unique=False)
    op.create_index(op.f('ix_features_creator_id'), 'features', ['creator_id'], unique=False)
    op.create_index(op.f('ix_features_owner_id'), 'features', ['owner_id'], unique=False)
    op.create_index(op.f('ix_features_team_id'), 'features', ['team_id'], unique=False)
    op.create_index(op.f('ix_features_product_area'), 'features', ['product_area'], unique=False)
    op.create_index(op.f('ix_features_tech_lead_id'), 'features', ['tech_lead_id'], unique=False)

    # Create notes table
    op.create_table('notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pb_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('creator_id', sa.Integer(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notes_id'), 'notes', ['id'], unique=False)
    op.create_index(op.f('ix_notes_pb_id'), 'notes', ['pb_id'], unique=True)
    op.create_index(op.f('ix_notes_state'), 'notes', ['state'], unique=False)
    op.create_index(op.f('ix_notes_creator_id'), 'notes', ['creator_id'], unique=False)
    op.create_index(op.f('ix_notes_owner_id'), 'notes', ['owner_id'], unique=False)
    op.create_index(op.f('ix_notes_team_id'), 'notes', ['team_id'], unique=False)
    op.create_index(op.f('ix_notes_customer_id'), 'notes', ['customer_id'], unique=False)

    # Create note_features junction table
    op.create_table('note_features',
        sa.Column('note_id', sa.Integer(), nullable=False),
        sa.Column('feature_id', sa.Integer(), nullable=False),
        sa.Column('linked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['feature_id'], ['features.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['note_id'], ['notes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('note_id', 'feature_id')
    )

    # Create feature_customers junction table
    op.create_table('feature_customers',
        sa.Column('feature_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('note_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['feature_id'], ['features.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('feature_id', 'customer_id')
    )

    # Create sync_history table
    op.create_table('sync_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('records_synced', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_history_id'), 'sync_history', ['id'], unique=False)
    op.create_index(op.f('ix_sync_history_entity_type'), 'sync_history', ['entity_type'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('sync_history')
    op.drop_table('feature_customers')
    op.drop_table('note_features')
    op.drop_table('notes')
    op.drop_table('features')
    op.drop_table('components')
    op.drop_table('customers')
    op.drop_table('companies')
    op.drop_table('teams')
    op.drop_table('users')
