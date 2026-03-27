"""payment_gateway_003 - Payment Gateway & Collection tables

Revision ID: payment_gw_003
Revises: billing_002
Create Date: gateway_payments, payment_receipts, payment_ledger, payment_refunds

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = "payment_gw_003"
down_revision = "billing_002"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    from sqlalchemy import inspect
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, "gateway_payments"):
        op.create_table(
            "gateway_payments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id"), nullable=False, index=True),
            sa.Column("payment_reference", sa.String(100), nullable=False),
            sa.Column("method", sa.String(20), nullable=False),
            sa.Column("provider", sa.String(30), nullable=True),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("currency", sa.String(5), nullable=False, server_default="INR"),
            sa.Column("status", sa.String(20), nullable=False, server_default="INITIATED"),
            sa.Column("transaction_id", sa.String(255), nullable=True),
            sa.Column("gateway_order_id", sa.String(255), nullable=True),
            sa.Column("gateway_signature", sa.String(500), nullable=True),
            sa.Column("collected_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata", postgresql.JSONB(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("uq_gateway_payments_payment_reference", "gateway_payments", ["payment_reference"], unique=True)
        # bill_id index is created by create_table (index=True on column)

    if not _table_exists(conn, "payment_receipts"):
        op.create_table(
            "payment_receipts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gateway_payments.id"), nullable=False, index=True),
            sa.Column("receipt_number", sa.String(50), nullable=False),
            sa.Column("pdf_path", sa.String(500), nullable=True),
            sa.Column("emailed_to", sa.String(255), nullable=True),
            sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists(conn, "payment_ledger"):
        op.create_table(
            "payment_ledger",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id"), nullable=False, index=True),
            sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gateway_payments.id"), nullable=True),
            sa.Column("entry_type", sa.String(20), nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("balance_after", sa.Numeric(12, 2), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists(conn, "payment_refunds"):
        op.create_table(
            "payment_refunds",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gateway_payments.id"), nullable=False, index=True),
            sa.Column("refund_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("refund_status", sa.String(20), nullable=False, server_default="SUCCESS"),
            sa.Column("gateway_refund_id", sa.String(255), nullable=True),
            sa.Column("refunded_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade():
    op.drop_table("payment_refunds")
    op.drop_table("payment_ledger")
    op.drop_table("payment_receipts")
    op.drop_index("uq_gateway_payments_payment_reference", table_name="gateway_payments")
    op.drop_table("gateway_payments")
