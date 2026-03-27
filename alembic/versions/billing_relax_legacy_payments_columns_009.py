"""billing_relax_legacy_payments_columns_009 - relax old invoice-style payments columns

Revision ID: billing_009
Revises: billing_008
Create Date: 2026-02-24

Older schemas created an invoice-centric `payments` table with many NOT NULL
columns (invoice_id, patient_id, payment_number, payment_date, payment_time,
payment_method, etc). The current billing module instead uses `bill_id` and
`payment_ref` via the BillingPayment model and does not populate these legacy
columns, which leads to NOT NULL violations when recording bill payments.

This migration relaxes those legacy columns to be NULLable so both schemas
can coexist safely.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_009"
down_revision = "billing_008"
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
        return

    # These types mirror the original initial_migration definitions.
    legacy_columns = {
        "invoice_id": postgresql.UUID(as_uuid=True),
        "patient_id": postgresql.UUID(as_uuid=True),
        "payment_number": sa.String(length=50),
        "transaction_id": sa.String(length=100),
        "payment_date": sa.String(length=10),
        "payment_time": sa.String(length=8),
        "payment_method": sa.String(length=50),
        "payment_details": postgresql.JSONB(astext_type=sa.Text()),
        "processed_by": postgresql.UUID(as_uuid=True),
        "processed_at": sa.DateTime(timezone=True),
        "gateway_name": sa.String(length=50),
        "gateway_response": postgresql.JSONB(astext_type=sa.Text()),
        "is_reconciled": sa.Boolean(),
        "reconciled_at": sa.DateTime(timezone=True),
        "reconciled_by": postgresql.UUID(as_uuid=True),
        "notes": sa.Text(),
    }

    for col_name, col_type in legacy_columns.items():
        if _column_exists(conn, "payments", col_name):
            op.alter_column(
                "payments",
                col_name,
                existing_type=col_type,
                nullable=True,
            )


def downgrade():
    # Best-effort downgrade: do nothing, since we don't want to re-enforce
    # NOT NULL on legacy columns in mixed-schema environments.
    pass

