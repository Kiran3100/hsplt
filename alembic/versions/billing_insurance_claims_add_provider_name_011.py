"""billing_insurance_claims_add_provider_name_011 - add insurance_provider_name to insurance_claims

Revision ID: billing_ins_claim_provider_011
Revises: billing_ins_claim_bill_010
Create Date: 2026-02-24

Older schemas created insurance_claims with a column named `insurance_provider`
instead of `insurance_provider_name`. The current InsuranceClaim model and
schemas expect `insurance_provider_name`, which causes UndefinedColumnError.

This migration adds `insurance_provider_name` if missing, without touching the
legacy `insurance_provider` column.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_ins_claim_provider_011"
down_revision = "billing_ins_claim_bill_010"
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
    if _table_exists(conn, "insurance_claims") and not _column_exists(conn, "insurance_claims", "insurance_provider_name"):
        op.add_column(
            "insurance_claims",
            sa.Column("insurance_provider_name", sa.String(length=255), nullable=True),
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "insurance_claims") and _column_exists(conn, "insurance_claims", "insurance_provider_name"):
        op.drop_column("insurance_claims", "insurance_provider_name")

