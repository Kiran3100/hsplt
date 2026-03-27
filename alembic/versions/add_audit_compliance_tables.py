"""Add audit trail and compliance tables

Revision ID: add_audit_compliance_tables
Revises: 129cde14c188
Create Date: 2026-01-29 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_audit_compliance_tables'
down_revision = 'd38c70f097c0'  # Branch from root: d38c70f097c0 -> add_audit_compliance_tables -> ... -> add_billing_001 (breaks cycle with 129cde14c188)
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    # Create lab_audit_logs table (idempotent: skip if already exists)
    if not _table_exists(conn, 'lab_audit_logs'):
        op.create_table('lab_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('performed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('performed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('reference_id', sa.String(length=100), nullable=True),
        sa.Column('is_critical', sa.Boolean(), nullable=False),
        sa.Column('requires_approval', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.ForeignKeyConstraint(['performed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_lab_audit_logs_action'), 'lab_audit_logs', ['action'], unique=False)
        op.create_index(op.f('ix_lab_audit_logs_entity_id'), 'lab_audit_logs', ['entity_id'], unique=False)
        op.create_index(op.f('ix_lab_audit_logs_entity_type'), 'lab_audit_logs', ['entity_type'], unique=False)
        op.create_index(op.f('ix_lab_audit_logs_hospital_id'), 'lab_audit_logs', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_lab_audit_logs_performed_at'), 'lab_audit_logs', ['performed_at'], unique=False)
        op.create_index(op.f('ix_lab_audit_logs_performed_by'), 'lab_audit_logs', ['performed_by'], unique=False)

    # Create chain_of_custody table (idempotent)
    if not _table_exists(conn, 'chain_of_custody'):
        op.create_table('chain_of_custody',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_no', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=20), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('from_user', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('to_user', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_location', sa.String(length=100), nullable=True),
        sa.Column('to_location', sa.String(length=100), nullable=False),
        sa.Column('equipment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('temperature', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('humidity', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('witness_signature', sa.String(length=255), nullable=True),
        sa.Column('seal_number', sa.String(length=50), nullable=True),
        sa.Column('condition_on_receipt', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['equipment_id'], ['lab_equipment.id'], ),
        sa.ForeignKeyConstraint(['from_user'], ['users.id'], ),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.ForeignKeyConstraint(['sample_id'], ['lab_samples.id'], ),
        sa.ForeignKeyConstraint(['to_user'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_chain_of_custody_event_timestamp'), 'chain_of_custody', ['event_timestamp'], unique=False)
        op.create_index(op.f('ix_chain_of_custody_hospital_id'), 'chain_of_custody', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_chain_of_custody_sample_id'), 'chain_of_custody', ['sample_id'], unique=False)
        op.create_index(op.f('ix_chain_of_custody_sample_no'), 'chain_of_custody', ['sample_no'], unique=False)

    # Create compliance_exports table (idempotent)
    if not _table_exists(conn, 'compliance_exports'):
        op.create_table('compliance_exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('export_type', sa.String(length=50), nullable=False),
        sa.Column('export_format', sa.String(length=10), nullable=False),
        sa.Column('from_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('to_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('exported_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('export_reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['exported_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_compliance_exports_export_type'), 'compliance_exports', ['export_type'], unique=False)
        op.create_index(op.f('ix_compliance_exports_hospital_id'), 'compliance_exports', ['hospital_id'], unique=False)


def downgrade():
    # Drop tables
    op.drop_index(op.f('ix_compliance_exports_hospital_id'), table_name='compliance_exports')
    op.drop_index(op.f('ix_compliance_exports_export_type'), table_name='compliance_exports')
    op.drop_table('compliance_exports')
    
    op.drop_index(op.f('ix_chain_of_custody_sample_no'), table_name='chain_of_custody')
    op.drop_index(op.f('ix_chain_of_custody_sample_id'), table_name='chain_of_custody')
    op.drop_index(op.f('ix_chain_of_custody_hospital_id'), table_name='chain_of_custody')
    op.drop_index(op.f('ix_chain_of_custody_event_timestamp'), table_name='chain_of_custody')
    op.drop_table('chain_of_custody')
    
    op.drop_index(op.f('ix_lab_audit_logs_performed_by'), table_name='lab_audit_logs')
    op.drop_index(op.f('ix_lab_audit_logs_performed_at'), table_name='lab_audit_logs')
    op.drop_index(op.f('ix_lab_audit_logs_hospital_id'), table_name='lab_audit_logs')
    op.drop_index(op.f('ix_lab_audit_logs_entity_type'), table_name='lab_audit_logs')
    op.drop_index(op.f('ix_lab_audit_logs_entity_id'), table_name='lab_audit_logs')
    op.drop_index(op.f('ix_lab_audit_logs_action'), table_name='lab_audit_logs')
    op.drop_table('lab_audit_logs')