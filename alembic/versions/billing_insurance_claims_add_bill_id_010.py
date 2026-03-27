"""billing_insurance_claims_add_bill_id_010 - ensure insurance_claims.bill_id exists

Revision ID: billing_ins_claim_bill_010
Revises: billing_009
Create Date: 2026-02-24

Older schemas created insurance_claims without bill_id (using invoice_id instead).
The current InsuranceClaim model and billing flows expect bill_id to be present.
This migration safely adds bill_id with a FK to bills.id if missing.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_ins_claim_bill_010"
down_revision = "billing_009"
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
    if _table_exists(conn, "insurance_claims") and not _column_exists(conn, "insurance_claims", "bill_id"):
        op.add_column(
            "insurance_claims",
            sa.Column("bill_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_insurance_claims_bill_id_bills",
            "insurance_claims",
            "bills",
            ["bill_id"],
            ["id"],
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "insurance_claims") and _column_exists(conn, "insurance_claims", "bill_id"):
        try:
            op.drop_constraint("fk_insurance_claims_bill_id_bills", "insurance_claims", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("insurance_claims", "bill_id")

