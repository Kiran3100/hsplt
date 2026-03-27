"""billing_relax_invoice_id_on_payments_007 - make legacy payments.invoice_id nullable

Revision ID: billing_007
Revises: billing_006
Create Date: 2026-02-24

Some databases started with the old invoice-centric schema from the initial
migration, where the `payments` table has a NOT NULL `invoice_id` column.
The current billing module uses `payments` as bill payments (via `bill_id`)
and does not set `invoice_id`, which causes NOT NULL violations.

This migration makes `payments.invoice_id` nullable IF the column exists,
so new bill payments can be inserted without breaking legacy data.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_007"
down_revision = "billing_006"
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
    if _table_exists(conn, "payments") and _column_exists(conn, "payments", "invoice_id"):
        # Relax NOT NULL constraint; legacy invoice-based flows can still populate it,
        # but new billing flows that only use bill_id won't be blocked.
        op.alter_column(
            "payments",
            "invoice_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )


def downgrade():
    # Best-effort: restore NOT NULL only if table/column still exist.
    conn = op.get_bind()
    if _table_exists(conn, "payments") and _column_exists(conn, "payments", "invoice_id"):
        op.alter_column(
            "payments",
            "invoice_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )

