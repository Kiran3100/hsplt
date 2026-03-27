"""Lab test catalogue: categories and test master fields

Revision ID: lab_catalogue_001
Revises: fix_pm_fk_001
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "lab_catalogue_001"
down_revision = "fix_pm_fk_001"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def _column_exists(conn, table, column):
    if not _table_exists(conn, table):
        return False
    return column in [c["name"] for c in inspect(conn).get_columns(table)]


def upgrade():
    conn = op.get_bind()

    if not _table_exists(conn, "lab_test_categories"):
        op.create_table(
            "lab_test_categories",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("category_code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_lab_test_categories_hospital_id", "lab_test_categories", ["hospital_id"], unique=False)
        op.create_index("ix_lab_test_categories_category_code", "lab_test_categories", ["category_code"], unique=False)
        op.create_index(
            "uq_lab_test_category_code_per_hospital",
            "lab_test_categories",
            ["hospital_id", "category_code"],
            unique=True,
        )

    if _table_exists(conn, "lab_tests"):
        if not _column_exists(conn, "lab_tests", "category_id"):
            op.add_column(
                "lab_tests",
                sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
            )
            op.create_foreign_key(
                "fk_lab_tests_category_id",
                "lab_tests",
                "lab_test_categories",
                ["category_id"],
                ["id"],
            )
            op.create_index("ix_lab_tests_category_id", "lab_tests", ["category_id"], unique=False)
        if not _column_exists(conn, "lab_tests", "unit"):
            op.add_column("lab_tests", sa.Column("unit", sa.String(length=50), nullable=True))
        if not _column_exists(conn, "lab_tests", "methodology"):
            op.add_column("lab_tests", sa.Column("methodology", sa.String(length=255), nullable=True))


def downgrade():
    conn = op.get_bind()

    if _table_exists(conn, "lab_tests"):
        if _column_exists(conn, "lab_tests", "methodology"):
            op.drop_column("lab_tests", "methodology")
        if _column_exists(conn, "lab_tests", "unit"):
            op.drop_column("lab_tests", "unit")
        if _column_exists(conn, "lab_tests", "category_id"):
            op.drop_constraint("fk_lab_tests_category_id", "lab_tests", type_="foreignkey")
            op.drop_index("ix_lab_tests_category_id", table_name="lab_tests")
            op.drop_column("lab_tests", "category_id")

    if _table_exists(conn, "lab_test_categories"):
        op.drop_index("uq_lab_test_category_code_per_hospital", table_name="lab_test_categories")
        op.drop_index("ix_lab_test_categories_category_code", table_name="lab_test_categories")
        op.drop_index("ix_lab_test_categories_hospital_id", table_name="lab_test_categories")
        op.drop_table("lab_test_categories")
