"""Add is_active column to bills table

Revision ID: add_is_active_bills_001
Revises: merge_all_heads
Create Date: 2026-02-24

Fixes: column "is_active" of relation "bills" does not exist.
The Bill model inherits from TenantBaseModel -> BaseModel which expects is_active;
the table may have been created without it by an older migration.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "add_is_active_bills_001"
down_revision = ("surgery_tables_012", "notif_infra_004")
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def _column_exists(conn, table, column):
    if table not in inspect(conn).get_table_names():
        return False
    return column in [c["name"] for c in inspect(conn).get_columns(table)]


def upgrade():
    conn = op.get_bind()
    if _table_exists(conn, "bills") and not _column_exists(conn, "bills", "is_active"):
        op.add_column(
            "bills",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "bills") and _column_exists(conn, "bills", "is_active"):
        op.drop_column("bills", "is_active")
