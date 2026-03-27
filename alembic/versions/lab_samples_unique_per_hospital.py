"""Lab samples: sample_no and barcode_value unique per hospital (multi-tenant)

Revision ID: lab_samples_003
Revises: lab_orders_002
Create Date: 2026-02-19

"""
from alembic import op
from sqlalchemy import inspect

revision = "lab_samples_003"
down_revision = "lab_orders_002"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    if "lab_samples" not in insp.get_table_names():
        return

    # Drop global unique constraints on sample_no and barcode_value
    for uc in insp.get_unique_constraints("lab_samples") or []:
        cols = uc.get("column_names") or []
        if cols == ["sample_no"] or cols == ["barcode_value"]:
            op.drop_constraint(uc["name"], "lab_samples", type_="unique")

    # Create unique per hospital; IF NOT EXISTS for idempotent runs
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_sample_no_per_hospital ON lab_samples (hospital_id, sample_no)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_barcode_value_per_hospital ON lab_samples (hospital_id, barcode_value)"
    )


def downgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    if "lab_samples" not in insp.get_table_names():
        return

    op.drop_index("uq_barcode_value_per_hospital", table_name="lab_samples")
    op.drop_index("uq_sample_no_per_hospital", table_name="lab_samples")
    op.create_unique_constraint("lab_samples_barcode_value_key", "lab_samples", ["barcode_value"])
    op.create_unique_constraint("lab_samples_sample_no_key", "lab_samples", ["sample_no"])
