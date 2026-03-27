"""Add telemed_provider_config for Hospital Admin provider config

Revision ID: telemed_006
Revises: telemed_005
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "telemed_006"
down_revision = "telemed_005"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if _table_exists(conn, "telemed_provider_config"):
        return
    op.create_table(
        "telemed_provider_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("default_provider", sa.String(20), nullable=False, server_default="WEBRTC"),
        sa.Column("enabled_providers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[\"WEBRTC\"]'::jsonb")),
        sa.Column("settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hospital_id", name="uq_telemed_provider_config_hospital_id"),
    )
    op.create_index("ix_telemed_provider_config_hospital_id", "telemed_provider_config", ["hospital_id"])


def downgrade():
    op.drop_index("ix_telemed_provider_config_hospital_id", table_name="telemed_provider_config")
    op.drop_table("telemed_provider_config")
