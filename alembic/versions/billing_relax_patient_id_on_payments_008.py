"""billing_relax_patient_id_on_payments_008 - make legacy payments.patient_id nullable

Revision ID: billing_008
Revises: billing_007
Create Date: 2026-02-24

Older invoice-centric schemas created `payments.patient_id` as NOT NULL.
The current BillingPayment model (bill-based) does not populate patient_id,
so we must relax this constraint to avoid NOT NULL violations when
recording bill payments.
"""

from alembic import op
from sqlalchemy.dialects import postgresql


revision = "billing_008"
down_revision = "billing_007"
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
    if _table_exists(conn, "payments") and _column_exists(conn, "payments", "patient_id"):
        op.alter_column(
            "payments",
            "patient_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "payments") and _column_exists(conn, "payments", "patient_id"):
        op.alter_column(
            "payments",
            "patient_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )

