"""add admissions.bed_id

Revision ID: add_admissions_bed_id
Revises: make_doctor_id_nullable
Create Date: 2026-02-22

Adds bed_id (FK to beds.id) to admissions for IPD bed assignment.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "add_admissions_bed_id"
down_revision = "make_doctor_id_nullable"
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
    if _table_exists(conn, "admissions") and not _column_exists(conn, "admissions", "bed_id"):
        op.add_column(
            "admissions",
            sa.Column("bed_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            "admissions_bed_id_fkey",
            "admissions",
            "beds",
            ["bed_id"],
            ["id"],
        )
        op.create_index("ix_admissions_bed_id", "admissions", ["bed_id"], unique=False)


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "admissions") and _column_exists(conn, "admissions", "bed_id"):
        op.drop_index("ix_admissions_bed_id", table_name="admissions")
        op.drop_constraint("admissions_bed_id_fkey", "admissions", type_="foreignkey")
        op.drop_column("admissions", "bed_id")
