"""billing_insurance_claims_relax_legacy_014 - relax legacy NOT NULL columns on insurance_claims

Revision ID: billing_ins_relax_014
Revises: billing_ins_inv_013
Create Date: 2026-02-25

Legacy schema for insurance_claims was invoice-centric and defined many NOT NULL
columns (invoice_id, claim_number, claim_date, treatment_date, etc.). The new
billing/insurance flow uses bill_id + patient_id + insurance_provider_name +
policy_number + claim_amount and does not populate those legacy fields, which
causes NOT NULL violations.

This migration relaxes those legacy columns to be nullable so the new flow
can create claims without DB errors.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "billing_ins_relax_014"
down_revision = "billing_ins_inv_013"
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

    # Map of legacy columns to their original types from initial migration
    legacy_cols = {
        "invoice_id": postgresql.UUID(as_uuid=True),
        "claim_number": sa.String(length=50),
        "insurance_tpa": sa.String(length=100),
        "claim_date": sa.String(length=10),
        "treatment_date": sa.String(length=10),
        "claimed_amount": sa.Numeric(12, 2),
        "deductible_amount": sa.Numeric(12, 2),
        "copay_amount": sa.Numeric(12, 2),
        "submitted_by": postgresql.UUID(as_uuid=True),
        "submitted_at": sa.DateTime(timezone=True),
        "reviewed_at": sa.DateTime(timezone=True),
        "approval_date": sa.String(length=10),
        "settlement_date": sa.String(length=10),
        "settlement_amount": sa.Numeric(12, 2),
        "supporting_documents": postgresql.JSONB(astext_type=sa.Text()),
        "notes": sa.Text(),
    }

    for col_name, col_type in legacy_cols.items():
        if _column_exists(conn, "insurance_claims", col_name):
            op.alter_column(
                "insurance_claims",
                col_name,
                existing_type=col_type,
                nullable=True,
            )


def downgrade():
    # Do not re-enforce NOT NULL on legacy columns in downgrade; no-op.
    pass

