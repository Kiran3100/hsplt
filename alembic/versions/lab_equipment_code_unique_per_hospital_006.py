"""Lab equipment: equipment_code unique per hospital + equipment-test mapping

Revision ID: lab_equipment_006
Revises: lab_reports_005
Create Date: 2026-02-19

"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "lab_equipment_006"
down_revision = "merge_lab_reports_equipment_001"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def _constraint_exists(conn, table, name):
    for uc in inspect(conn).get_unique_constraints(table) or []:
        if uc.get("name") == name:
            return True
    return False


def upgrade():
    conn = op.get_bind()
    if _table_exists(conn, "lab_equipment"):
        if not _constraint_exists(conn, "lab_equipment", "uq_equipment_code_per_hospital"):
            op.create_unique_constraint(
                "uq_equipment_code_per_hospital",
                "lab_equipment",
                ["hospital_id", "equipment_code"],
            )
    # lab_equipment is created in 19063f6ca87c (other branch); only create map if it exists
    if _table_exists(conn, "lab_equipment") and not _table_exists(conn, "lab_equipment_test_map"):
        op.create_table(
            "lab_equipment_test_map",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("equipment_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("test_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["equipment_id"], ["lab_equipment.id"]),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["test_id"], ["lab_tests.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_lab_equipment_test_map_equipment_id", "lab_equipment_test_map", ["equipment_id"])
        op.create_index("ix_lab_equipment_test_map_hospital_id", "lab_equipment_test_map", ["hospital_id"])
        op.create_index("ix_lab_equipment_test_map_test_id", "lab_equipment_test_map", ["test_id"])
        op.create_unique_constraint(
            "uq_equipment_test_per_map",
            "lab_equipment_test_map",
            ["equipment_id", "test_id"],
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "lab_equipment_test_map"):
        op.drop_constraint("uq_equipment_test_per_map", "lab_equipment_test_map", type_="unique")
        op.drop_index("ix_lab_equipment_test_map_test_id", table_name="lab_equipment_test_map")
        op.drop_index("ix_lab_equipment_test_map_hospital_id", table_name="lab_equipment_test_map")
        op.drop_index("ix_lab_equipment_test_map_equipment_id", table_name="lab_equipment_test_map")
        op.drop_table("lab_equipment_test_map")
    if _table_exists(conn, "lab_equipment"):
        op.drop_constraint("uq_equipment_code_per_hospital", "lab_equipment", type_="unique")
