"""billing_payments_refunds_002 - Refunds table for Payments module

Revision ID: billing_002
Revises: billing_001
Create Date: Add refunds table

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = "billing_002"
down_revision = "billing_001"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    from sqlalchemy import inspect
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, "refunds"):
        op.create_table(
            "refunds",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id"), nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="SUCCESS"),
            sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("refunded_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("gateway_refund_id", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade():
    op.drop_table("refunds")
