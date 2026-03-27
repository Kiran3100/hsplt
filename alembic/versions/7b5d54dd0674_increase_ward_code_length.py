"""increase_ward_code_length

Revision ID: 7b5d54dd0674
Revises: efd55c6d7099
Create Date: 2026-02-18 11:08:00.007179

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '7b5d54dd0674'
down_revision = '19063f6ca87c'  # 129cde14c188 -> 19063f6ca87c -> 7b5d54dd0674 -> make_doctor_id_nullable
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, 'wards'):
        return
    # Increase ward code column length from 20 to 100 characters
    op.alter_column('wards', 'code',
                    existing_type=sa.String(length=20),
                    type_=sa.String(length=100),
                    existing_nullable=False)


def downgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, 'wards'):
        return
    # Revert ward code column length back to 20 characters
    op.alter_column('wards', 'code',
                    existing_type=sa.String(length=100),
                    type_=sa.String(length=20),
                    existing_nullable=False)