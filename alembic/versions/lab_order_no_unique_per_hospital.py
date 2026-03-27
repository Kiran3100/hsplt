"""Lab order number unique per hospital (multi-tenant)

Revision ID: lab_orders_002
Revises: lab_catalogue_001
Create Date: 2026-02-19

"""
from alembic import op
from sqlalchemy import inspect

revision = "lab_orders_002"
down_revision = "lab_catalogue_001"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    if "lab_orders" not in insp.get_table_names():
        return

    # Drop global unique on lab_order_no (PostgreSQL names it lab_orders_lab_order_no_key or similar)
    for uc in insp.get_unique_constraints("lab_orders") or []:
        if uc.get("column_names") == ["lab_order_no"]:
            op.drop_constraint(uc["name"], "lab_orders", type_="unique")
            break

    # Create unique (hospital_id, lab_order_no); IF NOT EXISTS for idempotent runs
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_lab_order_no_per_hospital ON lab_orders (hospital_id, lab_order_no)"
    )


def downgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    if "lab_orders" not in insp.get_table_names():
        return

    op.drop_index("uq_lab_order_no_per_hospital", table_name="lab_orders")
    op.create_unique_constraint("lab_orders_lab_order_no_key", "lab_orders", ["lab_order_no"])
