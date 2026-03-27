"""
Make hospital_id nullable for users and patient_profiles to support
patient registration without choosing a hospital.

Revision ID: patient_hospital_nullable_001
Revises: lab_result_entry_003
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "patient_hospital_nullable_001"
down_revision = "lab_result_entry_003"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if _table_exists(conn, "users"):
        op.alter_column(
            "users",
            "hospital_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )
    if _table_exists(conn, "patient_profiles"):
        op.alter_column(
            "patient_profiles",
            "hospital_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "patient_profiles"):
        op.alter_column(
            "patient_profiles",
            "hospital_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )
    if _table_exists(conn, "users"):
        op.alter_column(
            "users",
            "hospital_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )




