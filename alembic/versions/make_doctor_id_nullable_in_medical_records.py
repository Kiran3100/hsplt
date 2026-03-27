"""make doctor_id nullable in medical_records

Revision ID: make_doctor_id_nullable
Revises: efd55c6d7099
Create Date: 2026-02-18 16:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'make_doctor_id_nullable'
down_revision = '7b5d54dd0674'  # Linear chain: 7b5d54dd0674 -> make_doctor_id_nullable (breaks cycle with merge)
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    """
    Make doctor_id nullable in medical_records table.
    This allows nurses to create medical records without a doctor.
    """
    conn = op.get_bind()
    if not _table_exists(conn, 'medical_records'):
        return
    op.alter_column('medical_records', 'doctor_id',
                    existing_type=sa.UUID(),
                    nullable=True)


def downgrade():
    """
    Revert doctor_id to NOT NULL.
    WARNING: This will fail if there are records with NULL doctor_id.
    """
    conn = op.get_bind()
    if not _table_exists(conn, 'medical_records'):
        return
    op.alter_column('medical_records', 'doctor_id',
                    existing_type=sa.UUID(),
                    nullable=False)
