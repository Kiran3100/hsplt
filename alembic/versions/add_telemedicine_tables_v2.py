"""Add telemedicine tables (standalone tele-appointments, sessions, participants)

Revision ID: telemed_001
Revises: lab_qc_007
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "telemed_001"
down_revision = "lab_qc_007"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()

    # 1. tele_appointments - standalone, no appointment_id (skip if exists for idempotent runs)
    if not _table_exists(conn, "tele_appointments"):
        op.create_table(
            "tele_appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="SCHEDULED"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_tele_appointments_doctor_id", "tele_appointments", ["doctor_id"], unique=False)
        op.create_index("ix_tele_appointments_hospital_id", "tele_appointments", ["hospital_id"], unique=False)
        op.create_index("ix_tele_appointments_patient_id", "tele_appointments", ["patient_id"], unique=False)
        op.create_index("ix_tele_appointments_scheduled_start", "tele_appointments", ["scheduled_start"], unique=False)
        op.create_index("ix_tele_appointments_status", "tele_appointments", ["status"], unique=False)

    # 2. telemed_sessions
    if not _table_exists(conn, "telemed_sessions"):
        op.create_table(
            "telemed_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tele_appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("provider", sa.String(20), nullable=False, server_default="WEBRTC"),
            sa.Column("room_name", sa.String(100), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="SCHEDULED"),
            sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("recording_enabled", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("recording_status", sa.String(20), nullable=True),
            sa.Column("recording_url", sa.Text(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("ended_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("end_reason", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.ForeignKeyConstraint(["ended_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["tele_appointment_id"], ["tele_appointments.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tele_appointment_id", name="uq_telemed_session_tele_appointment"),
        )
        op.create_index("ix_telemed_sessions_hospital_id", "telemed_sessions", ["hospital_id"], unique=False)
        op.create_index("ix_telemed_sessions_status", "telemed_sessions", ["status"], unique=False)
        op.create_index("ix_telemed_sessions_tele_appointment_id", "telemed_sessions", ["tele_appointment_id"], unique=True)

    # 3. telemed_participants
    if not _table_exists(conn, "telemed_participants"):
        op.create_table(
            "telemed_participants",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["session_id"], ["telemed_sessions.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("hospital_id", "session_id", "user_id", name="uq_telemed_participant_session_user"),
        )
        op.create_index("ix_telemed_participants_hospital_id", "telemed_participants", ["hospital_id"], unique=False)
        op.create_index("ix_telemed_participants_session_id", "telemed_participants", ["session_id"], unique=False)
        op.create_index("ix_telemed_participants_user_id", "telemed_participants", ["user_id"], unique=False)

    # 4. Restore FK: tele_prescriptions.tele_appointment_id -> tele_appointments.id (skip if table or FK missing)
    if not _table_exists(conn, "tele_prescriptions"):
        return
    insp = inspect(conn)
    fks = [fk for fk in (insp.get_foreign_keys("tele_prescriptions") or []) if fk.get("name") == "tele_prescriptions_tele_appointment_id_fkey"]
    if fks:
        return
    result = conn.execute(sa.text("SELECT COUNT(*) FROM tele_prescriptions"))
    count = result.scalar() or 0
    if count > 0:
        conn.execute(sa.text("DELETE FROM prescription_integrations"))
        conn.execute(sa.text("DELETE FROM prescription_pdfs"))
        conn.execute(sa.text("DELETE FROM prescription_lab_orders"))
        conn.execute(sa.text("DELETE FROM prescription_medicines"))
        conn.execute(sa.text("DELETE FROM tele_prescriptions"))
    op.create_foreign_key(
        "tele_prescriptions_tele_appointment_id_fkey",
        "tele_prescriptions",
        "tele_appointments",
        ["tele_appointment_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("tele_prescriptions_tele_appointment_id_fkey", "tele_prescriptions", type_="foreignkey")

    op.drop_index("ix_telemed_participants_user_id", table_name="telemed_participants")
    op.drop_index("ix_telemed_participants_session_id", table_name="telemed_participants")
    op.drop_index("ix_telemed_participants_hospital_id", table_name="telemed_participants")
    op.drop_table("telemed_participants")

    op.drop_index("ix_telemed_sessions_tele_appointment_id", table_name="telemed_sessions")
    op.drop_index("ix_telemed_sessions_status", table_name="telemed_sessions")
    op.drop_index("ix_telemed_sessions_hospital_id", table_name="telemed_sessions")
    op.drop_table("telemed_sessions")

    op.drop_index("ix_tele_appointments_status", table_name="tele_appointments")
    op.drop_index("ix_tele_appointments_scheduled_start", table_name="tele_appointments")
    op.drop_index("ix_tele_appointments_patient_id", table_name="tele_appointments")
    op.drop_index("ix_tele_appointments_hospital_id", table_name="tele_appointments")
    op.drop_index("ix_tele_appointments_doctor_id", table_name="tele_appointments")
    op.drop_table("tele_appointments")
