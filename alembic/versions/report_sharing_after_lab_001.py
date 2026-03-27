"""Create report sharing tables after lab chain (when 129cde14c188 ran before lab_orders existed)

Revision ID: report_sharing_after_lab_001
Revises: merge_heads_001
Create Date: 2026-02-22

When upgrading from a fresh DB, 129cde14c188 runs before lab_orders/lab_reports exist,
so it skips report_share_tokens and report_access_logs. This migration runs after the
merge (when lab tables exist) and creates them if missing.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "report_sharing_after_lab_001"
down_revision = "merge_heads_001"
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
    if not _table_exists(conn, "lab_orders") or not _table_exists(conn, "lab_reports"):
        return

    if not _table_exists(conn, "report_share_tokens"):
        op.create_table(
            "report_share_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lab_order_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lab_report_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False),
            sa.Column("allowed_viewer_type", sa.String(length=20), nullable=False),
            sa.Column("specific_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("revocation_reason", sa.Text(), nullable=True),
            sa.Column("access_count", sa.Integer(), nullable=False),
            sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_accessed_ip", sa.String(length=45), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["lab_order_id"], ["lab_orders.id"]),
            sa.ForeignKeyConstraint(["lab_report_id"], ["lab_reports.id"]),
            sa.ForeignKeyConstraint(["revoked_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["specific_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_report_share_tokens_expires_at"), "report_share_tokens", ["expires_at"], unique=False)
        op.create_index(op.f("ix_report_share_tokens_hospital_id"), "report_share_tokens", ["hospital_id"], unique=False)
        op.create_index(op.f("ix_report_share_tokens_lab_order_id"), "report_share_tokens", ["lab_order_id"], unique=False)
        op.create_index(op.f("ix_report_share_tokens_lab_report_id"), "report_share_tokens", ["lab_report_id"], unique=False)
        op.create_index(op.f("ix_report_share_tokens_token"), "report_share_tokens", ["token"], unique=True)

    if not _table_exists(conn, "report_access_logs"):
        op.create_table(
            "report_access_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lab_report_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lab_order_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("accessed_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("access_method", sa.String(length=20), nullable=False),
            sa.Column("share_token_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("access_type", sa.String(length=20), nullable=False),
            sa.Column("patient_id", sa.String(length=50), nullable=False),
            sa.Column("accessed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["accessed_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["lab_order_id"], ["lab_orders.id"]),
            sa.ForeignKeyConstraint(["lab_report_id"], ["lab_reports.id"]),
            sa.ForeignKeyConstraint(["share_token_id"], ["report_share_tokens.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_report_access_logs_accessed_at"), "report_access_logs", ["accessed_at"], unique=False)
        op.create_index(op.f("ix_report_access_logs_hospital_id"), "report_access_logs", ["hospital_id"], unique=False)
        op.create_index(op.f("ix_report_access_logs_lab_order_id"), "report_access_logs", ["lab_order_id"], unique=False)
        op.create_index(op.f("ix_report_access_logs_lab_report_id"), "report_access_logs", ["lab_report_id"], unique=False)
        op.create_index(op.f("ix_report_access_logs_patient_id"), "report_access_logs", ["patient_id"], unique=False)

    if _table_exists(conn, "lab_reports") and not _column_exists(conn, "lab_reports", "publish_status"):
        op.add_column("lab_reports", sa.Column("publish_status", sa.String(length=20), nullable=False, server_default="DRAFT"))
        op.add_column("lab_reports", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column("lab_reports", sa.Column("published_by", postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column("lab_reports", sa.Column("unpublished_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column("lab_reports", sa.Column("unpublished_by", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(None, "lab_reports", "users", ["published_by"], ["id"])
        op.create_foreign_key(None, "lab_reports", "users", ["unpublished_by"], ["id"])

    # prescription_notifications: create if skipped by prescription_notif_001 (tele_prescriptions didn't exist then)
    if _table_exists(conn, "tele_prescriptions") and not _table_exists(conn, "prescription_notifications"):
        op.create_table(
            "prescription_notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("prescription_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("event_type", sa.String(40), nullable=False),
            sa.Column("title", sa.String(255), nullable=True),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["prescription_id"], ["tele_prescriptions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_prescription_notifications_hospital_id"), "prescription_notifications", ["hospital_id"])
        op.create_index(op.f("ix_prescription_notifications_recipient_user_id"), "prescription_notifications", ["recipient_user_id"])
        op.create_index(op.f("ix_prescription_notifications_prescription_id"), "prescription_notifications", ["prescription_id"])
        op.create_index(op.f("ix_prescription_notifications_event_type"), "prescription_notifications", ["event_type"])


def downgrade():
    # Only drop tables/columns if this migration created them; leave downgrade no-op
    # to avoid breaking when 129cde14c188 created them.
    pass
