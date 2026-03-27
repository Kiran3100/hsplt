"""Add is_active to lab_orders and lab_order_items if missing

Revision ID: lab_orders_is_active_008
Revises: merge_heads_002
Create Date: 2026-02-23

Fixes: column "is_active" of relation "lab_orders" / "lab_order_items" does not exist.
The LabOrder and LabOrderItem models expect is_active; tables may have been created
without it by an older migration.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "lab_orders_is_active_008"
down_revision = "merge_heads_002"
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
    if _table_exists(conn, "lab_orders") and not _column_exists(conn, "lab_orders", "is_active"):
        op.add_column(
            "lab_orders",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if _table_exists(conn, "lab_order_items") and not _column_exists(conn, "lab_order_items", "is_active"):
        op.add_column(
            "lab_order_items",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "lab_orders") and _column_exists(conn, "lab_orders", "is_active"):
        op.drop_column("lab_orders", "is_active")
    if _table_exists(conn, "lab_order_items") and _column_exists(conn, "lab_order_items", "is_active"):
        op.drop_column("lab_order_items", "is_active")
