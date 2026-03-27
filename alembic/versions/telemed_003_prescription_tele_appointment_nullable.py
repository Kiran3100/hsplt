"""Make tele_prescriptions.tele_appointment_id nullable

Revision ID: telemed_003
Revises: telemed_002
Create Date: 2026-02-19

"""
from alembic import op
from sqlalchemy import inspect

revision = "telemed_003"
down_revision = "telemed_002"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if "tele_prescriptions" not in inspect(conn).get_table_names():
        return
    op.alter_column(
        "tele_prescriptions",
        "tele_appointment_id",
        existing_type=None,
        nullable=True,
    )


def downgrade():
    conn = op.get_bind()
    if "tele_prescriptions" not in inspect(conn).get_table_names():
        return
    op.alter_column(
        "tele_prescriptions",
        "tele_appointment_id",
        existing_type=None,
        nullable=False,
    )
