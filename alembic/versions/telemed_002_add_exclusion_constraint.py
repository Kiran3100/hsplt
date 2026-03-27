"""Add exclusion constraint for tele_appointments overlap prevention

Revision ID: telemed_002
Revises: telemed_001
Create Date: 2026-02-19

"""
from alembic import op
from sqlalchemy import inspect

revision = "telemed_002"
down_revision = "telemed_001"
branch_labels = None
depends_on = None


def _table_has_column(conn, table, column):
    if table not in inspect(conn).get_table_names():
        return False
    return column in [c["name"] for c in inspect(conn).get_columns(table)]


def upgrade():
    conn = op.get_bind()
    # Only apply if tele_appointments has scheduled_start (from telemed_001 schema) and not already altered
    if not _table_has_column(conn, "tele_appointments", "scheduled_start"):
        return
    if _table_has_column(conn, "tele_appointments", "time_range"):
        return
    # btree_gist required for UUID in EXCLUDE
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # Add generated tstzrange column (for timestamptz)
    op.execute("""
        ALTER TABLE tele_appointments
        ADD COLUMN time_range tstzrange
        GENERATED ALWAYS AS (tstzrange(scheduled_start, scheduled_end, '[)')) STORED
    """)

    # Exclusion: no overlapping (hospital_id, doctor_id) for non-terminal statuses
    op.execute("""
        ALTER TABLE tele_appointments
        ADD CONSTRAINT uq_tele_appointments_no_overlap
        EXCLUDE USING gist (hospital_id WITH =, doctor_id WITH =, time_range WITH &&)
        WHERE (status NOT IN ('CANCELLED', 'COMPLETED', 'MISSED'))
    """)


def downgrade():
    conn = op.get_bind()
    if not _table_has_column(conn, "tele_appointments", "time_range"):
        return
    op.execute("ALTER TABLE tele_appointments DROP CONSTRAINT IF EXISTS uq_tele_appointments_no_overlap")
    op.execute("ALTER TABLE tele_appointments DROP COLUMN IF EXISTS time_range")
