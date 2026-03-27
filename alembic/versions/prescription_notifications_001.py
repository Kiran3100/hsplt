"""Add prescription_notifications for in-app prescription event notifications

Revision ID: prescription_notif_001
Revises: telemed_006
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "prescription_notif_001"
down_revision = "telemed_006"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if _table_exists(conn, "prescription_notifications"):
        return
    # Only create when tele_prescriptions exists (it's created in eadec4bba3a0 on another branch)
    if not _table_exists(conn, "tele_prescriptions"):
        return
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
    op.create_index("ix_prescription_notifications_hospital_id", "prescription_notifications", ["hospital_id"])
    op.create_index("ix_prescription_notifications_recipient_user_id", "prescription_notifications", ["recipient_user_id"])
    op.create_index("ix_prescription_notifications_prescription_id", "prescription_notifications", ["prescription_id"])
    op.create_index("ix_prescription_notifications_event_type", "prescription_notifications", ["event_type"])


def downgrade():
    op.drop_index("ix_prescription_notifications_event_type", table_name="prescription_notifications")
    op.drop_index("ix_prescription_notifications_prescription_id", table_name="prescription_notifications")
    op.drop_index("ix_prescription_notifications_recipient_user_id", table_name="prescription_notifications")
    op.drop_index("ix_prescription_notifications_hospital_id", table_name="prescription_notifications")
    op.drop_table("prescription_notifications")
