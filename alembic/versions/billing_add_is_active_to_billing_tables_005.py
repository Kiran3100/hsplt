"""billing_add_is_active_to_billing_tables_005 - ensure is_active on billing tables

Revision ID: billing_005
Revises: billing_004
Create Date: 2026-02-24

Adds missing is_active columns for billing tables whose SQLAlchemy models
inherit from TenantBaseModel but whose original migrations did not create
the column. This prevents UndefinedColumnError when inserting/selecting.
"""

from alembic import op
import sqlalchemy as sa


revision = "billing_005"
down_revision = "billing_004"
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


def _ensure_is_active(table: str) -> None:
    """Add is_active BOOLEAN with default TRUE if missing on given table."""
    conn = op.get_bind()
    if _table_exists(conn, table) and not _column_exists(conn, table, "is_active"):
        op.add_column(
            table,
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def upgrade():
    # Align DB schema with TenantBaseModel for all billing tables.
    for tbl in ("bills", "payments", "ipd_charges", "financial_documents", "insurance_claims", "reconciliations"):
        _ensure_is_active(tbl)


def downgrade():
    conn = op.get_bind()
    from sqlalchemy import inspect

    insp = inspect(conn)
    for tbl in ("bills", "payments", "ipd_charges", "financial_documents", "insurance_claims", "reconciliations"):
        if tbl in insp.get_table_names() and _column_exists(conn, tbl, "is_active"):
            op.drop_column(tbl, "is_active")

