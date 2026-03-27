"""Lab result approval and versioning: approved_by/approved_at, previous_result_id, drop one-result-per-item

Revision ID: lab_result_004
Revises: lab_samples_003
Create Date: 2026-02-19

"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "lab_result_004"
down_revision = "lab_samples_003"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def _column_exists(conn, table, column):
    return column in [c["name"] for c in inspect(conn).get_columns(table)]


def _index_exists(conn, table, index_name):
    for idx in inspect(conn).get_indexes(table) or []:
        if idx.get("name") == index_name:
            return True
    for uc in inspect(conn).get_unique_constraints(table) or []:
        if uc.get("name") == index_name:
            return True
    return False


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, "test_results"):
        return

    # Add pathologist approval and versioning columns
    if not _column_exists(conn, "test_results", "approved_by"):
        op.add_column(
            "test_results",
            sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_test_results_approved_by_users",
            "test_results",
            "users",
            ["approved_by"],
            ["id"],
        )
    if not _column_exists(conn, "test_results", "approved_at"):
        op.add_column(
            "test_results",
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists(conn, "test_results", "signature_placeholder"):
        op.add_column(
            "test_results",
            sa.Column("signature_placeholder", sa.Text(), nullable=True),
        )
    if not _column_exists(conn, "test_results", "previous_result_id"):
        op.add_column(
            "test_results",
            sa.Column("previous_result_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_test_results_previous_result_id",
            "test_results",
            "test_results",
            ["previous_result_id"],
            ["id"],
        )
        op.create_index(
            op.f("ix_test_results_previous_result_id"),
            "test_results",
            ["previous_result_id"],
            unique=False,
        )

    # Allow multiple result versions per order item (drop one-result-per-item unique)
    if _index_exists(conn, "test_results", "uq_test_result_per_order_item"):
        op.drop_index("uq_test_result_per_order_item", table_name="test_results")


def downgrade():
    conn = op.get_bind()
    if not _table_exists(conn, "test_results"):
        return

    # Restore one-result-per-item unique (only safe if at most one result per order_item)
    op.create_index(
        "uq_test_result_per_order_item",
        "test_results",
        ["lab_order_item_id"],
        unique=True,
    )

    # Remove versioning and approval columns
    if _column_exists(conn, "test_results", "previous_result_id"):
        op.drop_index(
            op.f("ix_test_results_previous_result_id"),
            table_name="test_results",
        )
        op.drop_constraint(
            "fk_test_results_previous_result_id",
            "test_results",
            type_="foreignkey",
        )
        op.drop_column("test_results", "previous_result_id")
    if _column_exists(conn, "test_results", "signature_placeholder"):
        op.drop_column("test_results", "signature_placeholder")
    if _column_exists(conn, "test_results", "approved_at"):
        op.drop_column("test_results", "approved_at")
    if _column_exists(conn, "test_results", "approved_by"):
        op.drop_constraint(
            "fk_test_results_approved_by_users",
            "test_results",
            type_="foreignkey",
        )
        op.drop_column("test_results", "approved_by")
