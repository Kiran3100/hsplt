"""Add is_active to lab_samples and sample_order_items if missing

Revision ID: lab_samples_is_active_010
Revises: lab_order_items_is_active_009
Create Date: 2026-02-23

Fixes: column "is_active" of relation "lab_samples" does not exist.
Ensures new and existing DBs have is_active on lab_samples (and sample_order_items).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "lab_samples_is_active_010"
down_revision = "lab_order_items_is_active_009"
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
    if _table_exists(conn, "lab_samples") and not _column_exists(conn, "lab_samples", "is_active"):
        op.add_column(
            "lab_samples",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if _table_exists(conn, "sample_order_items") and not _column_exists(conn, "sample_order_items", "is_active"):
        op.add_column(
            "sample_order_items",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "lab_samples") and _column_exists(conn, "lab_samples", "is_active"):
        op.drop_column("lab_samples", "is_active")
    if _table_exists(conn, "sample_order_items") and _column_exists(conn, "sample_order_items", "is_active"):
        op.drop_column("sample_order_items", "is_active")
