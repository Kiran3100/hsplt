"""Add lab test registration tables

Revision ID: lab_test_registration_001
Revises: efd55c6d7099
Create Date: 2026-01-29 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'lab_test_registration_001'
down_revision = 'd38c70f097c0'  # Branch from initial (efd55c6d7099 was missing)
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    # Create lab_tests table (idempotent: skip if exists)
    if not _table_exists(conn, 'lab_tests'):
        op.create_table('lab_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_code', sa.String(length=50), nullable=False),
        sa.Column('test_name', sa.String(length=255), nullable=False),
        sa.Column('sample_type', sa.String(length=20), nullable=False),
        sa.Column('turnaround_time_hours', sa.Integer(), nullable=False),
        sa.Column('price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('preparation_instructions', sa.Text(), nullable=True),
        sa.Column('reference_ranges', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_lab_tests_hospital_id'), 'lab_tests', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_lab_tests_test_code'), 'lab_tests', ['test_code'], unique=False)
        op.create_index('uq_test_code_per_hospital', 'lab_tests', ['hospital_id', 'test_code'], unique=True)

    if not _table_exists(conn, 'lab_orders'):
        op.create_table('lab_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_order_no', sa.String(length=50), nullable=False),
        sa.Column('patient_id', sa.String(length=50), nullable=False),
        sa.Column('requested_by_doctor_id', sa.String(length=50), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('encounter_id', sa.String(length=50), nullable=True),
        sa.Column('prescription_id', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('special_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('sample_collection_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('cancelled_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lab_order_no')
        )
        op.create_index(op.f('ix_lab_orders_hospital_id'), 'lab_orders', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_lab_orders_lab_order_no'), 'lab_orders', ['lab_order_no'], unique=False)
        op.create_index(op.f('ix_lab_orders_patient_id'), 'lab_orders', ['patient_id'], unique=False)
        op.create_index(op.f('ix_lab_orders_requested_by_doctor_id'), 'lab_orders', ['requested_by_doctor_id'], unique=False)

    if not _table_exists(conn, 'lab_order_items'):
        op.create_table('lab_order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('sample_collected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_values', sa.JSON(), nullable=True),
        sa.Column('result_notes', sa.Text(), nullable=True),
        sa.Column('verified_by', sa.String(length=100), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], ),
        sa.ForeignKeyConstraint(['test_id'], ['lab_tests.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_lab_order_items_lab_order_id'), 'lab_order_items', ['lab_order_id'], unique=False)
        op.create_index(op.f('ix_lab_order_items_test_id'), 'lab_order_items', ['test_id'], unique=False)

    # Add FK for hospital_id in lab_orders only if missing (idempotent)
    if _table_exists(conn, 'lab_orders'):
        insp = inspect(conn)
        fks = [fk for fk in insp.get_foreign_keys('lab_orders') if (fk.get('constrained_columns') or []) == ['hospital_id']]
        if not fks:
            op.create_foreign_key('lab_orders_hospital_id_fkey', 'lab_orders', 'hospitals', ['hospital_id'], ['id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('lab_order_items')
    op.drop_table('lab_orders')
    op.drop_table('lab_tests')