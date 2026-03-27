"""Add lab result entry and report tables

Revision ID: lab_result_entry_003
Revises: lab_sample_collection_002
Create Date: 2026-01-29 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'lab_result_entry_003'
down_revision = 'lab_sample_collection_002'
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, 'test_results'):
        op.create_table('test_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_order_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('entered_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('released_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('rejected_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('technical_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['entered_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.ForeignKeyConstraint(['lab_order_item_id'], ['lab_order_items.id'], ),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['released_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['sample_id'], ['lab_samples.id'], ),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_test_results_hospital_id'), 'test_results', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_test_results_lab_order_item_id'), 'test_results', ['lab_order_item_id'], unique=False)
        op.create_index(op.f('ix_test_results_sample_id'), 'test_results', ['sample_id'], unique=False)
        op.create_index('uq_test_result_per_order_item', 'test_results', ['lab_order_item_id'], unique=True)

    if not _table_exists(conn, 'result_values'):
        op.create_table('result_values',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parameter_name', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=100), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('reference_range', sa.String(length=100), nullable=True),
        sa.Column('flag', sa.String(length=20), nullable=True),
        sa.Column('is_abnormal', sa.Boolean(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['test_result_id'], ['test_results.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_result_values_test_result_id'), 'result_values', ['test_result_id'], unique=False)

    if not _table_exists(conn, 'lab_reports'):
        op.create_table('lab_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_number', sa.String(length=50), nullable=False),
        sa.Column('report_version', sa.Integer(), nullable=False),
        sa.Column('pdf_path', sa.String(length=500), nullable=True),
        sa.Column('pdf_blob_ref', sa.String(length=500), nullable=True),
        sa.Column('report_data', sa.JSON(), nullable=True),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('total_tests', sa.Integer(), nullable=False),
        sa.Column('completed_tests', sa.Integer(), nullable=False),
        sa.Column('is_final', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_number')
        )
        op.create_index(op.f('ix_lab_reports_hospital_id'), 'lab_reports', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_lab_reports_lab_order_id'), 'lab_reports', ['lab_order_id'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('lab_reports')
    op.drop_table('result_values')
    op.drop_table('test_results')