"""Merge heads: add_admissions_bed_id and report_sharing_after_lab_001

Revision ID: merge_heads_002
Revises: add_admissions_bed_id, report_sharing_after_lab_001
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa

revision = "merge_heads_002"
down_revision = ("add_admissions_bed_id", "report_sharing_after_lab_001")
branch_labels = None
depends_on = None


def upgrade():
    # Merge only: no schema changes
    pass


def downgrade():
    pass
