"""billing_payments_add_bill_id_003 - ensure payments.bill_id column exists

Revision ID: billing_003
Revises: billing_002
Create Date: Add bill_id column to payments if missing
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_003"
down_revision = "billing_002"
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
    if _table_exists(conn, "payments") and not _column_exists(conn, "payments", "bill_id"):
        # Add nullable first to avoid issues on existing rows; application logic will enforce non-null for new data.
        op.add_column(
            "payments",
            sa.Column("bill_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_payments_bill_id_bills",
            "payments",
            "bills",
            ["bill_id"],
            ["id"],
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "payments") and _column_exists(conn, "payments", "bill_id"):
        # Drop FK first, then column
        try:
            op.drop_constraint("fk_payments_bill_id_bills", "payments", type_="foreignkey")
        except Exception:
            # Constraint may not exist; ignore
            pass
        op.drop_column("payments", "bill_id")

