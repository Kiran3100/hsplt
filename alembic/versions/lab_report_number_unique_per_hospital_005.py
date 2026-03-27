"""Lab reports: report_number unique per hospital (multi-tenant)

Revision ID: lab_reports_005
Revises: lab_result_004
Create Date: 2026-02-19

"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

revision = "lab_reports_005"
down_revision = "lab_result_004"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def _drop_global_unique_on_report_number(conn):
    """Drop any global unique constraint or index on report_number."""
    insp = inspect(conn)
    # Unique constraints on lab_reports
    for uc in insp.get_unique_constraints("lab_reports") or []:
        cols = uc.get("column_names") or []
        if cols == ["report_number"]:
            op.drop_constraint(uc["name"], "lab_reports", type_="unique")
            return
    # Unique indexes
    for idx in insp.get_indexes("lab_reports") or []:
        if idx.get("unique") and (idx.get("column_names") or []) == ["report_number"]:
            op.drop_index(idx["name"], table_name="lab_reports")
            return


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, "lab_reports"):
        return
    # Skip if per-hospital unique already exists (idempotent)
    insp = inspect(conn)
    for uc in insp.get_unique_constraints("lab_reports") or []:
        if uc.get("name") == "uq_report_number_per_hospital" or (uc.get("column_names") or []) == ["hospital_id", "report_number"]:
            return
    _drop_global_unique_on_report_number(conn)
    op.create_unique_constraint(
        "uq_report_number_per_hospital",
        "lab_reports",
        ["hospital_id", "report_number"],
    )


def downgrade():
    conn = op.get_bind()
    if not _table_exists(conn, "lab_reports"):
        return
    op.drop_constraint("uq_report_number_per_hospital", "lab_reports", type_="unique")
    op.create_unique_constraint("lab_reports_report_number_key", "lab_reports", ["report_number"])
