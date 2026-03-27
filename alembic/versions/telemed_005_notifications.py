"""Add telemed_notifications for in-app notification records

Revision ID: telemed_005
Revises: telemed_004
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "telemed_005"
down_revision = "telemed_004"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if _table_exists(conn, "telemed_notifications"):
        return
    op.create_table(
        "telemed_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["telemed_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telemed_notifications_hospital_id", "telemed_notifications", ["hospital_id"])
    op.create_index("ix_telemed_notifications_recipient_user_id", "telemed_notifications", ["recipient_user_id"])
    op.create_index("ix_telemed_notifications_session_id", "telemed_notifications", ["session_id"])
    op.create_index("ix_telemed_notifications_event_type", "telemed_notifications", ["event_type"])
    op.create_index("ix_telemed_notifications_created_at", "telemed_notifications", ["created_at"])


def downgrade():
    op.drop_index("ix_telemed_notifications_created_at", table_name="telemed_notifications")
    op.drop_index("ix_telemed_notifications_event_type", table_name="telemed_notifications")
    op.drop_index("ix_telemed_notifications_session_id", table_name="telemed_notifications")
    op.drop_index("ix_telemed_notifications_recipient_user_id", table_name="telemed_notifications")
    op.drop_index("ix_telemed_notifications_hospital_id", table_name="telemed_notifications")
    op.drop_table("telemed_notifications")
