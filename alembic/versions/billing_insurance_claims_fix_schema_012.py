"""billing_insurance_claims_fix_schema_012 - align insurance_claims with InsuranceClaim model

Revision ID: billing_ins_claim_fix_012
Revises: billing_ins_claim_provider_011
Create Date: 2026-02-24

Some databases were created from older invoice-based schemas where the
`insurance_claims` table did not have all columns expected by the current
InsuranceClaim model (bill_id, insurance_provider_name, claim_amount, etc.).

This migration safely adds any missing columns used by the model so that
the entire insurance module works without manual DB fixes.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_ins_claim_fix_012"
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
    if not _table_exists(conn, "insurance_claims"):
        return

    # Columns required by app.models.billing.insurance_claim.InsuranceClaim
    required_columns = {
        "bill_id": postgresql.UUID(as_uuid=True),
        "patient_id": postgresql.UUID(as_uuid=True),
        "insurance_provider_name": sa.String(length=255),
        "policy_number": sa.String(length=100),
        "claim_amount": sa.Numeric(12, 2),
        "approved_amount": sa.Numeric(12, 2),
        "status": sa.String(length=20),
        "rejection_reason": sa.Text(),
        "settlement_reference": sa.String(length=100),
    }

    for col_name, col_type in required_columns.items():
        if not _column_exists(conn, "insurance_claims", col_name):
            if col_name == "bill_id":
                # bill_id already added in previous migration, but keep logic safe
                op.add_column(
                    "insurance_claims",
                    sa.Column(col_name, col_type, nullable=True),
                )
                op.create_foreign_key(
                    "fk_insurance_claims_bill_id_bills",
                    "insurance_claims",
                    "bills",
                    ["bill_id"],
                    ["id"],
                )
            elif col_name == "patient_id":
                op.add_column(
                    "insurance_claims",
                    sa.Column(col_name, col_type, nullable=True),
                )
            elif col_name == "claim_amount":
                op.add_column(
                    "insurance_claims",
                    sa.Column(col_name, col_type, nullable=True, server_default="0"),
                )
            elif col_name == "approved_amount":
                op.add_column(
                    "insurance_claims",
                    sa.Column(col_name, col_type, nullable=True),
                )
            elif col_name == "status":
                op.add_column(
                    "insurance_claims",
                    sa.Column(col_name, col_type, nullable=False, server_default="CREATED"),
                )
            else:
                # policy_number, insurance_provider_name, rejection_reason, settlement_reference
                op.add_column(
                    "insurance_claims",
                    sa.Column(col_name, col_type, nullable=True),
                )


def downgrade():
    # Best-effort: do not aggressively drop columns in downgrade for mixed-schema environments.
    pass

