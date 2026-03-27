"""Add updated_at to sample_order_items if missing

Revision ID: sample_order_updated_at_011
Revises: lab_samples_is_active_010
Create Date: 2026-02-23

Fixes: column sample_order_items.updated_at does not exist.
BaseModel expects updated_at; table may have been created without it.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "sample_order_updated_at_011"
down_revision = "lab_samples_is_active_010"
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
    if _table_exists(conn, "sample_order_items") and not _column_exists(conn, "sample_order_items", "updated_at"):
        op.add_column(
            "sample_order_items",
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "sample_order_items") and _column_exists(conn, "sample_order_items", "updated_at"):
        op.drop_column("sample_order_items", "updated_at")
