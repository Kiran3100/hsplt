"""Merge all migration heads into one

Revision ID: merge_heads_001
Revises: 067683c1dab3, make_doctor_id_nullable, patient_hospital_nullable_001, notif_infra_004
Create Date: Merge multiple heads so 'alembic upgrade head' works

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "merge_heads_001"
down_revision = (
    "067683c1dab3",
    "make_doctor_id_nullable",
    "patient_hospital_nullable_001",
    "notif_infra_004",
)
branch_labels = None
depends_on = None


def upgrade():
    # Merge migration: no schema changes, just unifies history
    pass


def downgrade():
    pass
