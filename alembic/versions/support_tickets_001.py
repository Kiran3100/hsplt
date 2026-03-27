"""support_tickets_001 - Support tickets for Super Admin helpdesk

Revision ID: support_tickets_001
Revises: fix_999_merge_all_heads
Create Date: Support tickets table for escalations

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "support_tickets_001"
down_revision = "fix_999_merge_all_heads"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    from sqlalchemy import inspect
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if _table_exists(conn, "support_tickets"):
        return
    uuid_col = postgresql.UUID(as_uuid=True)
    op.create_table(
        "support_tickets",
        sa.Column("id", uuid_col, primary_key=True),
        sa.Column("hospital_id", uuid_col, sa.ForeignKey("hospitals.id"), nullable=False, index=True),
        sa.Column("raised_by_user_id", uuid_col, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("assigned_to_user_id", uuid_col, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "support_tickets"):
        op.drop_table("support_tickets")
