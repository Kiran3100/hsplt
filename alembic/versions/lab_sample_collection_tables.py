"""Add lab sample collection tables

Revision ID: lab_sample_collection_002
Revises: lab_test_registration_001
Create Date: 2026-01-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'lab_sample_collection_002'
down_revision = 'lab_test_registration_001'
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, 'lab_samples'):
        op.create_table('lab_samples',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_no', sa.String(length=50), nullable=False),
        sa.Column('barcode_value', sa.String(length=100), nullable=False),
        sa.Column('qr_value', sa.String(length=100), nullable=True),
        sa.Column('lab_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', sa.String(length=50), nullable=False),
        sa.Column('sample_type', sa.String(length=20), nullable=False),
        sa.Column('container_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('collected_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('collection_site', sa.String(length=20), nullable=True),
        sa.Column('collector_notes', sa.Text(), nullable=True),
        sa.Column('received_in_lab_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_location', sa.String(length=100), nullable=True),
        sa.Column('received_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rejection_reason', sa.String(length=30), nullable=True),
        sa.Column('rejection_notes', sa.Text(), nullable=True),
        sa.Column('volume_ml', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['collected_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], ),
        sa.ForeignKeyConstraint(['received_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sample_no'),
        sa.UniqueConstraint('barcode_value')
        )
        op.create_index(op.f('ix_lab_samples_hospital_id'), 'lab_samples', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_lab_samples_lab_order_id'), 'lab_samples', ['lab_order_id'], unique=False)
        op.create_index(op.f('ix_lab_samples_patient_id'), 'lab_samples', ['patient_id'], unique=False)
        op.create_index(op.f('ix_lab_samples_barcode_value'), 'lab_samples', ['barcode_value'], unique=False)
        op.create_index(op.f('ix_lab_samples_qr_value'), 'lab_samples', ['qr_value'], unique=False)

    if not _table_exists(conn, 'sample_order_items'):
        op.create_table('sample_order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_order_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lab_order_item_id'], ['lab_order_items.id'], ),
        sa.ForeignKeyConstraint(['sample_id'], ['lab_samples.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_sample_order_items_sample_id'), 'sample_order_items', ['sample_id'], unique=False)
        op.create_index(op.f('ix_sample_order_items_lab_order_item_id'), 'sample_order_items', ['lab_order_item_id'], unique=False)
        op.create_index('uq_sample_order_item_mapping', 'sample_order_items', ['sample_id', 'lab_order_item_id'], unique=True)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('sample_order_items')
    op.drop_table('lab_samples')