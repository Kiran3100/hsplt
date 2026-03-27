"""billing_insurance_claims_relax_invoice_id_013 - make insurance_claims.invoice_id nullable

Revision ID: billing_ins_inv_013
Revises: billing_ins_claim_amount_012
Create Date: 2026-02-25

Legacy schema for insurance_claims used a NOT NULL invoice_id FK to invoices.
Current flows use bill_id instead and do not set invoice_id, which causes
NOT NULL violations. This migration relaxes invoice_id to be nullable.
"""

from alembic import op
from sqlalchemy.dialects import postgresql


revision = "billing_ins_inv_013"
down_revision = "billing_ins_claim_amount_012"
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
    if _table_exists(conn, "insurance_claims") and _column_exists(conn, "insurance_claims", "invoice_id"):
        op.alter_column(
            "insurance_claims",
            "invoice_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "insurance_claims") and _column_exists(conn, "insurance_claims", "invoice_id"):
        op.alter_column(
            "insurance_claims",
            "invoice_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )

