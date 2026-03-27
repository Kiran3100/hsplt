"""Add telemed_messages, telemed_files, telemed_consultation_notes, telemed_vitals; session_id on tele_prescriptions

Revision ID: telemed_004
Revises: telemed_003
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "telemed_004"
down_revision = "telemed_003"
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
    # Only create tables that FK to telemed_sessions when that table exists
    if not _table_exists(conn, "telemed_sessions"):
        return

    # 1. telemed_messages
    if not _table_exists(conn, "telemed_messages"):
        op.create_table(
            "telemed_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("sender_role", sa.String(20), nullable=False),
            sa.Column("message_type", sa.String(20), nullable=False, server_default="TEXT"),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("file_ref", sa.String(500), nullable=True),
            sa.Column("content_encrypted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("key_ref", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["session_id"], ["telemed_sessions.id"]),
            sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_telemed_messages_hospital_id", "telemed_messages", ["hospital_id"])
        op.create_index("ix_telemed_messages_session_id", "telemed_messages", ["session_id"])
        op.create_index("ix_telemed_messages_sender_id", "telemed_messages", ["sender_id"])

    # 2. telemed_files
    if not _table_exists(conn, "telemed_files"):
        op.create_table(
            "telemed_files",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("mime_type", sa.String(100), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=True),
            sa.Column("storage_url", sa.Text(), nullable=True),
            sa.Column("checksum", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["session_id"], ["telemed_sessions.id"]),
            sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_telemed_files_hospital_id", "telemed_files", ["hospital_id"])
        op.create_index("ix_telemed_files_session_id", "telemed_files", ["session_id"])
        op.create_index("ix_telemed_files_uploaded_by", "telemed_files", ["uploaded_by"])

    # 3. telemed_consultation_notes
    if not _table_exists(conn, "telemed_consultation_notes"):
        op.create_table(
            "telemed_consultation_notes",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("soap_json", sa.Text(), nullable=True),
            sa.Column("soap_text", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["session_id"], ["telemed_sessions.id"]),
            sa.ForeignKeyConstraint(["doctor_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_telemed_consultation_notes_hospital_id", "telemed_consultation_notes", ["hospital_id"])
        op.create_index("ix_telemed_consultation_notes_session_id", "telemed_consultation_notes", ["session_id"])
        op.create_index("ix_telemed_consultation_notes_doctor_id", "telemed_consultation_notes", ["doctor_id"])

    # 4. telemed_vitals
    if not _table_exists(conn, "telemed_vitals"):
        op.create_table(
            "telemed_vitals",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("vitals_type", sa.String(20), nullable=False),
            sa.Column("value_json", sa.Text(), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("entered_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
            sa.ForeignKeyConstraint(["session_id"], ["telemed_sessions.id"]),
            sa.ForeignKeyConstraint(["entered_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_telemed_vitals_hospital_id", "telemed_vitals", ["hospital_id"])
        op.create_index("ix_telemed_vitals_patient_id", "telemed_vitals", ["patient_id"])
        op.create_index("ix_telemed_vitals_session_id", "telemed_vitals", ["session_id"])
        op.create_index("ix_telemed_vitals_vitals_type", "telemed_vitals", ["vitals_type"])
        op.create_index("ix_telemed_vitals_recorded_at", "telemed_vitals", ["recorded_at"])

    # 5. Add session_id to tele_prescriptions (skip if already present)
    if _table_exists(conn, "tele_prescriptions") and not _column_exists(conn, "tele_prescriptions", "session_id"):
        op.add_column("tele_prescriptions", sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "tele_prescriptions_session_id_fkey",
            "tele_prescriptions",
            "telemed_sessions",
            ["session_id"],
            ["id"],
        )
        op.create_index("ix_tele_prescriptions_session_id", "tele_prescriptions", ["session_id"])


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "tele_prescriptions") and _column_exists(conn, "tele_prescriptions", "session_id"):
        op.drop_index("ix_tele_prescriptions_session_id", table_name="tele_prescriptions")
        op.drop_constraint("tele_prescriptions_session_id_fkey", "tele_prescriptions", type_="foreignkey")
        op.drop_column("tele_prescriptions", "session_id")

    if _table_exists(conn, "telemed_vitals"):
        op.drop_index("ix_telemed_vitals_recorded_at", table_name="telemed_vitals")
        op.drop_index("ix_telemed_vitals_vitals_type", table_name="telemed_vitals")
        op.drop_index("ix_telemed_vitals_session_id", table_name="telemed_vitals")
        op.drop_index("ix_telemed_vitals_patient_id", table_name="telemed_vitals")
        op.drop_index("ix_telemed_vitals_hospital_id", table_name="telemed_vitals")
        op.drop_table("telemed_vitals")

    if _table_exists(conn, "telemed_consultation_notes"):
        op.drop_index("ix_telemed_consultation_notes_doctor_id", table_name="telemed_consultation_notes")
        op.drop_index("ix_telemed_consultation_notes_session_id", table_name="telemed_consultation_notes")
        op.drop_index("ix_telemed_consultation_notes_hospital_id", table_name="telemed_consultation_notes")
        op.drop_table("telemed_consultation_notes")

    if _table_exists(conn, "telemed_files"):
        op.drop_index("ix_telemed_files_uploaded_by", table_name="telemed_files")
        op.drop_index("ix_telemed_files_session_id", table_name="telemed_files")
        op.drop_index("ix_telemed_files_hospital_id", table_name="telemed_files")
        op.drop_table("telemed_files")

    if _table_exists(conn, "telemed_messages"):
        op.drop_index("ix_telemed_messages_sender_id", table_name="telemed_messages")
        op.drop_index("ix_telemed_messages_session_id", table_name="telemed_messages")
        op.drop_index("ix_telemed_messages_hospital_id", table_name="telemed_messages")
        op.drop_table("telemed_messages")
