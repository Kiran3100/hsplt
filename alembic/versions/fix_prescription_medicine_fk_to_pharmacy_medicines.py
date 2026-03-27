"""fix prescription_medicines.medicine_id FK to pharmacy_medicines

Revision ID: fix_pm_fk_001
Revises: pharmacy_001
Create Date: 2026-02-19

Changes prescription_medicines.medicine_id foreign key from medicines.id
to pharmacy_medicines.id so it points to the pharmacy medicine catalog.
Only runs if prescription_medicines exists (created in eadec4bba3a0 on another branch).
"""
from alembic import op
from sqlalchemy import inspect

# revision identifiers
revision = 'fix_pm_fk_001'
down_revision = 'pharmacy_001'
branch_labels = None
depends_on = None


def _table_exists(connection, name):
    return name in inspect(connection).get_table_names()


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, 'prescription_medicines') or not _table_exists(conn, 'pharmacy_medicines'):
        return
    # Drop existing FK (name may vary; PostgreSQL default is tablename_columnname_fkey)
    op.execute(
        "ALTER TABLE prescription_medicines DROP CONSTRAINT IF EXISTS prescription_medicines_medicine_id_fkey"
    )
    # Add correct FK to pharmacy_medicines
    op.create_foreign_key(
        'prescription_medicines_medicine_id_fkey',
        'prescription_medicines',
        'pharmacy_medicines',
        ['medicine_id'],
        ['id']
    )


def downgrade():
    conn = op.get_bind()
    if not _table_exists(conn, 'prescription_medicines'):
        return
    op.execute(
        "ALTER TABLE prescription_medicines DROP CONSTRAINT IF EXISTS prescription_medicines_medicine_id_fkey"
    )
    # Restore original FK to medicines.id only if that table exists
    if _table_exists(conn, 'medicines'):
        op.create_foreign_key(
            'prescription_medicines_medicine_id_fkey',
            'prescription_medicines',
            'medicines',
            ['medicine_id'],
            ['id']
        )
