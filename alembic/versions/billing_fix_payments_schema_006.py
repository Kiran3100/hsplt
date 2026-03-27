"""billing_fix_payments_schema_006 - align payments table with BillingPayment model

Revision ID: billing_006
Revises: billing_005
Create Date: 2026-02-24

Some databases may have an older or partial `payments` table definition that
is missing columns used by the BillingPayment SQLAlchemy model and billing
services. This migration safely adds any missing columns with sensible
defaults/nullable flags so that the billing module works without manual DB fixes.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_006"
down_revision = "billing_005"
branch_labels = None
depends_on = None


def _table_exists(conn, name: str) -> bool:
    from sqlalchemy import inspect

    return name in inspect(conn).get_table_names()


def _column_exists(conn, table: str, column: str) -> bool:
    from sqlalchemy import inspect

    insp = inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(col["name"] == column for col in insp.get_columns(table))


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, "payments"):
        # Nothing to do if table itself doesn't exist (will be created by billing_001 on new DBs)
        return

    # Core multi-tenant column
    if not _column_exists(conn, "payments", "hospital_id"):
        op.add_column(
            "payments",
            sa.Column(
                "hospital_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("hospitals.id"),
                nullable=True,
            ),
        )

    # Link to bills
    if not _column_exists(conn, "payments", "bill_id"):
        op.add_column(
            "payments",
            sa.Column(
                "bill_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("bills.id"),
                nullable=True,
            ),
        )

    # Business columns expected by BillingPayment model
    if not _column_exists(conn, "payments", "payment_ref"):
        op.add_column("payments", sa.Column("payment_ref", sa.String(length=100), nullable=True))
        op.create_index(
            "uq_payments_payment_ref",
            "payments",
            ["payment_ref"],
            unique=True,
        )

    if not _column_exists(conn, "payments", "method"):
        op.add_column("payments", sa.Column("method", sa.String(length=30), nullable=True))

    if not _column_exists(conn, "payments", "provider"):
        op.add_column("payments", sa.Column("provider", sa.String(length=50), nullable=True))

    if not _column_exists(conn, "payments", "amount"):
        op.add_column(
            "payments",
            sa.Column("amount", sa.Numeric(12, 2), nullable=True, server_default="0"),
        )

    if not _column_exists(conn, "payments", "status"):
        op.add_column(
            "payments",
            sa.Column("status", sa.String(length=20), nullable=True, server_default="INITIATED"),
        )

    if not _column_exists(conn, "payments", "paid_at"):
        op.add_column(
            "payments",
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _column_exists(conn, "payments", "collected_by_user_id"):
        op.add_column(
            "payments",
            sa.Column(
                "collected_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
        )

    if not _column_exists(conn, "payments", "gateway_transaction_id"):
        op.add_column(
            "payments",
            sa.Column("gateway_transaction_id", sa.String(length=255), nullable=True),
        )

    if not _column_exists(conn, "payments", "extra_data"):
        op.add_column(
            "payments",
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )

    # Audit / lifecycle columns from BaseModel / TenantBaseModel
    if not _column_exists(conn, "payments", "is_active"):
        op.add_column(
            "payments",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    if not _column_exists(conn, "payments", "created_at"):
        op.add_column(
            "payments",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _column_exists(conn, "payments", "updated_at"):
        op.add_column(
            "payments",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade():
    # Best-effort downgrade: we only drop columns we added, and ignore errors if they don't exist.
    conn = op.get_bind()
    if not _table_exists(conn, "payments"):
        return

    def safe_drop_column(name: str):
        if _column_exists(conn, "payments", name):
            op.drop_column("payments", name)

    # Drop index before dropping column
    try:
        op.drop_index("uq_payments_payment_ref", table_name="payments")
    except Exception:
        pass

    for col in [
        "payment_ref",
        "method",
        "provider",
        "amount",
        "status",
        "paid_at",
        "collected_by_user_id",
        "gateway_transaction_id",
        "extra_data",
        "bill_id",
        "hospital_id",
        "is_active",
        "created_at",
        "updated_at",
    ]:
        safe_drop_column(col)

