"""Add report sharing and notification tables

Revision ID: 129cde14c188
Revises: 19063f6ca87c
Create Date: 2026-01-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '129cde14c188'
down_revision = 'd38c70f097c0'  # Branch from root: d38c70f097c0 -> 129cde14c188 -> 19063f6ca87c -> 7b5d54dd0674 -> make_doctor_id_nullable
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def _column_exists(conn, table, column):
    if table not in inspect(conn).get_table_names():
        return False
    return column in [c["name"] for c in inspect(conn).get_columns(table)]


def upgrade():
    conn = op.get_bind()
    lab_tables_exist = _table_exists(conn, 'lab_orders') and _table_exists(conn, 'lab_reports')

    # Create report_share_tokens table only when lab_orders and lab_reports exist (they have FKs to them)
    if lab_tables_exist and not _table_exists(conn, 'report_share_tokens'):
        op.create_table('report_share_tokens',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('lab_order_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('lab_report_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('token', sa.String(length=255), nullable=False),
            sa.Column('token_hash', sa.String(length=255), nullable=False),
            sa.Column('allowed_viewer_type', sa.String(length=20), nullable=False),
            sa.Column('specific_user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('revoked_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('revocation_reason', sa.Text(), nullable=True),
            sa.Column('access_count', sa.Integer(), nullable=False),
            sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_accessed_ip', sa.String(length=45), nullable=True),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
            sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], ),
            sa.ForeignKeyConstraint(['lab_report_id'], ['lab_reports.id'], ),
            sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['specific_user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_report_share_tokens_expires_at'), 'report_share_tokens', ['expires_at'], unique=False)
        op.create_index(op.f('ix_report_share_tokens_hospital_id'), 'report_share_tokens', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_report_share_tokens_lab_order_id'), 'report_share_tokens', ['lab_order_id'], unique=False)
        op.create_index(op.f('ix_report_share_tokens_lab_report_id'), 'report_share_tokens', ['lab_report_id'], unique=False)
        op.create_index(op.f('ix_report_share_tokens_token'), 'report_share_tokens', ['token'], unique=True)

    # Create notification_outbox table
    if not _table_exists(conn, 'notification_outbox'):
        op.create_table('notification_outbox',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('event_type', sa.String(length=30), nullable=False),
            sa.Column('event_id', sa.String(length=100), nullable=False),
            sa.Column('recipient_type', sa.String(length=20), nullable=False),
            sa.Column('recipient_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('recipient_email', sa.String(length=255), nullable=True),
            sa.Column('recipient_phone', sa.String(length=20), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('payload', sa.JSON(), nullable=True),
            sa.Column('channel', sa.String(length=20), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('failure_reason', sa.Text(), nullable=True),
            sa.Column('retry_count', sa.Integer(), nullable=False),
            sa.Column('max_retries', sa.Integer(), nullable=False),
            sa.Column('external_id', sa.String(length=255), nullable=True),
            sa.Column('external_status', sa.String(length=50), nullable=True),
            sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
            sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_notification_outbox_event_id'), 'notification_outbox', ['event_id'], unique=False)
        op.create_index(op.f('ix_notification_outbox_event_type'), 'notification_outbox', ['event_type'], unique=False)
        op.create_index(op.f('ix_notification_outbox_hospital_id'), 'notification_outbox', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_notification_outbox_recipient_id'), 'notification_outbox', ['recipient_id'], unique=False)

    # Create report_access_logs table only when lab tables and report_share_tokens exist
    if lab_tables_exist and not _table_exists(conn, 'report_access_logs'):
        op.create_table('report_access_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('lab_report_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('lab_order_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('accessed_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('access_method', sa.String(length=20), nullable=False),
            sa.Column('share_token_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('access_type', sa.String(length=20), nullable=False),
            sa.Column('patient_id', sa.String(length=50), nullable=False),
            sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['accessed_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
            sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], ),
            sa.ForeignKeyConstraint(['lab_report_id'], ['lab_reports.id'], ),
            sa.ForeignKeyConstraint(['share_token_id'], ['report_share_tokens.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_report_access_logs_accessed_at'), 'report_access_logs', ['accessed_at'], unique=False)
        op.create_index(op.f('ix_report_access_logs_hospital_id'), 'report_access_logs', ['hospital_id'], unique=False)
        op.create_index(op.f('ix_report_access_logs_lab_order_id'), 'report_access_logs', ['lab_order_id'], unique=False)
        op.create_index(op.f('ix_report_access_logs_lab_report_id'), 'report_access_logs', ['lab_report_id'], unique=False)
        op.create_index(op.f('ix_report_access_logs_patient_id'), 'report_access_logs', ['patient_id'], unique=False)

    # Add publish status to lab_reports table (skip if columns already exist)
    if _table_exists(conn, 'lab_reports') and not _column_exists(conn, 'lab_reports', 'publish_status'):
        op.add_column('lab_reports', sa.Column('publish_status', sa.String(length=20), nullable=False, server_default='DRAFT'))
        op.add_column('lab_reports', sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
        op.add_column('lab_reports', sa.Column('published_by', postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column('lab_reports', sa.Column('unpublished_at', sa.DateTime(timezone=True), nullable=True))
        op.add_column('lab_reports', sa.Column('unpublished_by', postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(None, 'lab_reports', 'users', ['published_by'], ['id'])
        op.create_foreign_key(None, 'lab_reports', 'users', ['unpublished_by'], ['id'])


def downgrade():
    # Remove foreign key constraints first
    op.drop_constraint(None, 'lab_reports', type_='foreignkey')
    op.drop_constraint(None, 'lab_reports', type_='foreignkey')
    
    # Remove columns from lab_reports
    op.drop_column('lab_reports', 'unpublished_by')
    op.drop_column('lab_reports', 'unpublished_at')
    op.drop_column('lab_reports', 'published_by')
    op.drop_column('lab_reports', 'published_at')
    op.drop_column('lab_reports', 'publish_status')
    
    # Drop tables
    op.drop_index(op.f('ix_report_access_logs_patient_id'), table_name='report_access_logs')
    op.drop_index(op.f('ix_report_access_logs_lab_report_id'), table_name='report_access_logs')
    op.drop_index(op.f('ix_report_access_logs_lab_order_id'), table_name='report_access_logs')
    op.drop_index(op.f('ix_report_access_logs_hospital_id'), table_name='report_access_logs')
    op.drop_index(op.f('ix_report_access_logs_accessed_at'), table_name='report_access_logs')
    op.drop_table('report_access_logs')
    
    op.drop_index(op.f('ix_notification_outbox_recipient_id'), table_name='notification_outbox')
    op.drop_index(op.f('ix_notification_outbox_hospital_id'), table_name='notification_outbox')
    op.drop_index(op.f('ix_notification_outbox_event_type'), table_name='notification_outbox')
    op.drop_index(op.f('ix_notification_outbox_event_id'), table_name='notification_outbox')
    op.drop_table('notification_outbox')
    
    op.drop_index(op.f('ix_report_share_tokens_token'), table_name='report_share_tokens')
    op.drop_index(op.f('ix_report_share_tokens_lab_report_id'), table_name='report_share_tokens')
    op.drop_index(op.f('ix_report_share_tokens_lab_order_id'), table_name='report_share_tokens')
    op.drop_index(op.f('ix_report_share_tokens_hospital_id'), table_name='report_share_tokens')
    op.drop_index(op.f('ix_report_share_tokens_expires_at'), table_name='report_share_tokens')
    op.drop_table('report_share_tokens')