"""billing_insurance_claims_add_claim_amount_012 - add claim_amount to insurance_claims

Revision ID: billing_ins_claim_amount_012
Revises: billing_ins_claim_provider_011
Create Date: 2026-02-24

Legacy schema used `claimed_amount` on insurance_claims.
Current InsuranceClaim model expects `claim_amount`.
This migration adds claim_amount if missing and backfills it from claimed_amount when present.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_ins_claim_amount_012"
down_revision = "billing_ins_claim_provider_011"
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
    if _table_exists(conn, "insurance_claims") and not _column_exists(conn, "insurance_claims", "claim_amount"):
        op.add_column(
            "insurance_claims",
            sa.Column("claim_amount", sa.Numeric(12, 2), nullable=True),
        )
        # Best-effort backfill from legacy claimed_amount if it exists
        if _column_exists(conn, "insurance_claims", "claimed_amount"):
            conn.execute(
                sa.text(
                    "UPDATE insurance_claims SET claim_amount = claimed_amount WHERE claim_amount IS NULL"
                )
            )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "insurance_claims") and _column_exists(conn, "insurance_claims", "claim_amount"):
        op.drop_column("insurance_claims", "claim_amount")

