"""billing_insurance_claims_relax_provider_015 - make insurance_claims.insurance_provider nullable

Revision ID: billing_ins_prov_015
Revises: billing_ins_relax_014
Create Date: 2026-02-25

Legacy schema defined insurance_claims.insurance_provider as NOT NULL.
New code uses insurance_provider_name instead, leaving insurance_provider NULL.
Relax insurance_provider to be nullable to avoid NOT NULL violations.
"""

from alembic import op
import sqlalchemy as sa


revision = "billing_ins_prov_015"
down_revision = "billing_ins_relax_014"
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
    if _table_exists(conn, "insurance_claims") and _column_exists(conn, "insurance_claims", "insurance_provider"):
        op.alter_column(
            "insurance_claims",
            "insurance_provider",
            existing_type=sa.String(length=100),
            nullable=True,
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "insurance_claims") and _column_exists(conn, "insurance_claims", "insurance_provider"):
        op.alter_column(
            "insurance_claims",
            "insurance_provider",
            existing_type=sa.String(length=100),
            nullable=False,
        )

