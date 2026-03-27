"""billing_payments_add_payment_ref_004 - ensure payments.payment_ref column exists

Revision ID: billing_004
Revises: billing_003
Create Date: Add payment_ref column to payments if missing
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_004"
down_revision = "billing_003"
branch_labels = None
depends_on = None


def _table_exists(conn, name: str) -> bool:
    from sqlalchemy import inspect

    return name in inspect(conn).get_table_names()


def _column_exists(conn, table: str, column: str) -> bool:
    from sqlalchemy import inspect

    insp = inspect(conn)
    for col in insp.get_columns(table):
        if col["name"] == column:
            return True
    return False


def upgrade():
    conn = op.get_bind()
    if _table_exists(conn, "payments") and not _column_exists(conn, "payments", "payment_ref"):
        op.add_column(
            "payments",
            sa.Column("payment_ref", sa.String(length=100), nullable=True),
        )
        # Optional but useful: unique constraint for idempotency; allows multiple NULLs in Postgres
        op.create_index(
            "uq_payments_payment_ref",
            "payments",
            ["payment_ref"],
            unique=True,
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "payments") and _column_exists(conn, "payments", "payment_ref"):
        try:
            op.drop_index("uq_payments_payment_ref", table_name="payments")
        except Exception:
            pass
        op.drop_column("payments", "payment_ref")

