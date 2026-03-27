"""Lab QC: deviation_notes on qc_runs + qc_corrective_actions table

Revision ID: lab_qc_007
Revises: lab_equipment_006
Create Date: 2026-02-19

"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "lab_qc_007"
down_revision = "lab_equipment_006"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def _column_exists(conn, table, column):
    return column in [c["name"] for c in inspect(conn).get_columns(table)]


def upgrade():
    conn = op.get_bind()
    if _table_exists(conn, "qc_runs") and not _column_exists(conn, "qc_runs", "deviation_notes"):
        op.add_column("qc_runs", sa.Column("deviation_notes", sa.Text(), nullable=True))
    if not _table_exists(conn, "qc_corrective_actions"):
        op.create_table(
            "qc_corrective_actions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("qc_run_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("action_taken", sa.Text(), nullable=False),
            sa.Column("performed_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["performed_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["qc_run_id"], ["qc_runs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_qc_corrective_actions_hospital_id", "qc_corrective_actions", ["hospital_id"])
        op.create_index("ix_qc_corrective_actions_qc_run_id", "qc_corrective_actions", ["qc_run_id"])


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "qc_corrective_actions"):
        op.drop_index("ix_qc_corrective_actions_qc_run_id", table_name="qc_corrective_actions")
        op.drop_index("ix_qc_corrective_actions_hospital_id", table_name="qc_corrective_actions")
        op.drop_table("qc_corrective_actions")
    if _table_exists(conn, "qc_runs") and _column_exists(conn, "qc_runs", "deviation_notes"):
        op.drop_column("qc_runs", "deviation_notes")
