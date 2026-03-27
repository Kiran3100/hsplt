"""Add is_active to lab_order_items if missing

Revision ID: lab_order_items_is_active_009
Revises: lab_orders_is_active_008
Create Date: 2026-02-23

Fixes: column "is_active" of relation "lab_order_items" does not exist.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "lab_order_items_is_active_009"
down_revision = "lab_orders_is_active_008"
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
    if _table_exists(conn, "lab_order_items") and not _column_exists(conn, "lab_order_items", "is_active"):
        op.add_column(
            "lab_order_items",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "lab_order_items") and _column_exists(conn, "lab_order_items", "is_active"):
        op.drop_column("lab_order_items", "is_active")
