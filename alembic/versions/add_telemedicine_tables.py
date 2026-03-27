"""Add telemedicine tables

Revision ID: add_telemedicine_tables
Revises: add_audit_compliance_tables
Create Date: 2026-01-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_telemedicine_tables'
down_revision = 'add_audit_compliance_tables'
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    # Skip if tele_appointments already exists (e.g. from telemed_001 on another branch)
    if _table_exists(conn, 'tele_appointments'):
        return
    # Create tele_appointments table
    op.create_table('tele_appointments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scheduled_date', sa.String(length=10), nullable=False),
        sa.Column('start_time', sa.String(length=8), nullable=False),
        sa.Column('end_time', sa.String(length=8), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('session_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('cancelled_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ),
        sa.ForeignKeyConstraint(['cancelled_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.ForeignKeyConstraint(['patient_id'], ['patient_profiles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('appointment_id')
    )
    op.create_index(op.f('ix_tele_appointments_appointment_id'), 'tele_appointments', ['appointment_id'], unique=False)
    op.create_index(op.f('ix_tele_appointments_doctor_id'), 'tele_appointments', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_tele_appointments_hospital_id'), 'tele_appointments', ['hospital_id'], unique=False)
    op.create_index(op.f('ix_tele_appointments_patient_id'), 'tele_appointments', ['patient_id'], unique=False)
    op.create_index(op.f('ix_tele_appointments_scheduled_date'), 'tele_appointments', ['scheduled_date'], unique=False)
    op.create_index(op.f('ix_tele_appointments_status'), 'tele_appointments', ['status'], unique=False)

    # Create video_sessions table
    op.create_table('video_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tele_appointment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('doctor_join_token', sa.String(length=500), nullable=False),
        sa.Column('patient_join_token', sa.String(length=500), nullable=False),
        sa.Column('session_start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('room_name', sa.String(length=100), nullable=True),
        sa.Column('max_participants', sa.Integer(), nullable=False),
        sa.Column('doctor_joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('patient_joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('doctor_left_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('patient_left_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('end_reason', sa.String(length=50), nullable=True),
        sa.Column('provider_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ended_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.ForeignKeyConstraint(['tele_appointment_id'], ['tele_appointments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_video_sessions_hospital_id'), 'video_sessions', ['hospital_id'], unique=False)
    op.create_index(op.f('ix_video_sessions_session_id'), 'video_sessions', ['session_id'], unique=False)
    op.create_index(op.f('ix_video_sessions_status'), 'video_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_video_sessions_tele_appointment_id'), 'video_sessions', ['tele_appointment_id'], unique=False)


def downgrade() -> None:
    # Drop video_sessions table
    op.drop_index(op.f('ix_video_sessions_tele_appointment_id'), table_name='video_sessions')
    op.drop_index(op.f('ix_video_sessions_status'), table_name='video_sessions')
    op.drop_index(op.f('ix_video_sessions_session_id'), table_name='video_sessions')
    op.drop_index(op.f('ix_video_sessions_hospital_id'), table_name='video_sessions')
    op.drop_table('video_sessions')
    
    # Drop tele_appointments table
    op.drop_index(op.f('ix_tele_appointments_status'), table_name='tele_appointments')
    op.drop_index(op.f('ix_tele_appointments_scheduled_date'), table_name='tele_appointments')
    op.drop_index(op.f('ix_tele_appointments_patient_id'), table_name='tele_appointments')
    op.drop_index(op.f('ix_tele_appointments_hospital_id'), table_name='tele_appointments')
    op.drop_index(op.f('ix_tele_appointments_doctor_id'), table_name='tele_appointments')
    op.drop_index(op.f('ix_tele_appointments_appointment_id'), table_name='tele_appointments')
    op.drop_table('tele_appointments')