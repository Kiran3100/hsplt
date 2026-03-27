"""Merge lab_reports_005 and 19063f6ca87c so lab_equipment_006 runs after lab_equipment exists

Revision ID: merge_lab_reports_equipment_001
Revises: lab_reports_005, 19063f6ca87c
Create Date: Ensures lab_equipment table exists before lab_equipment_test_map is created

"""
from alembic import op


revision = "merge_lab_reports_equipment_001"
down_revision = ("lab_reports_005", "19063f6ca87c")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
