"""notification_infrastructure_004 - Notification providers, templates, preferences, jobs, delivery_logs

Revision ID: notif_infra_004
Revises: payment_gw_003
Create Date: Notification Infrastructure (outbox, multi-channel, OTP, scheduling)

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


revision = "notif_infra_004"
down_revision = "payment_gw_003"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    from sqlalchemy import inspect
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    uuid_col = postgresql.UUID(as_uuid=True)
    jsonb = postgresql.JSONB()

    if not _table_exists(conn, "notification_providers"):
        op.create_table(
            "notification_providers",
            sa.Column("id", uuid_col, primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", uuid_col, sa.ForeignKey("hospitals.id"), nullable=True, index=True),
            sa.Column("provider_type", sa.String(20), nullable=False),
            sa.Column("provider_name", sa.String(30), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("config", jsonb, nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists(conn, "notification_templates"):
        op.create_table(
            "notification_templates",
            sa.Column("id", uuid_col, primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", uuid_col, sa.ForeignKey("hospitals.id"), nullable=True, index=True),
            sa.Column("channel", sa.String(20), nullable=False),
            sa.Column("template_key", sa.String(80), nullable=False),
            sa.Column("subject", sa.String(255), nullable=True),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index(
            "uq_notification_templates_hospital_template_key",
            "notification_templates",
            ["hospital_id", "template_key"],
            unique=True,
        )

    if not _table_exists(conn, "notification_preferences"):
        op.create_table(
            "notification_preferences",
            sa.Column("id", uuid_col, primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", uuid_col, sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("owner_type", sa.String(20), nullable=False),
            sa.Column("owner_id", uuid_col, nullable=False, index=True),
            sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("quiet_hours_start", sa.Time(), nullable=True),
            sa.Column("quiet_hours_end", sa.Time(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists(conn, "notification_jobs"):
        op.create_table(
            "notification_jobs",
            sa.Column("id", uuid_col, primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", uuid_col, sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("event_type", sa.String(60), nullable=False, index=True),
            sa.Column("channel", sa.String(20), nullable=False),
            sa.Column("to_address", sa.String(255), nullable=False),
            sa.Column("template_id", uuid_col, sa.ForeignKey("notification_templates.id"), nullable=True),
            sa.Column("payload", jsonb, nullable=True),
            sa.Column("subject_rendered", sa.String(255), nullable=True),
            sa.Column("message_rendered", sa.Text(), nullable=True),
            sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED", index=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("provider_message_id", sa.String(255), nullable=True),
            sa.Column("idempotency_key", sa.String(120), nullable=False, index=True),
            sa.Column("created_by_user_id", uuid_col, sa.ForeignKey("users.id"), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("uq_notification_jobs_idempotency_key", "notification_jobs", ["idempotency_key"], unique=True)

    if not _table_exists(conn, "notification_delivery_logs"):
        op.create_table(
            "notification_delivery_logs",
            sa.Column("id", uuid_col, primary_key=True, default=uuid.uuid4),
            sa.Column("job_id", uuid_col, sa.ForeignKey("notification_jobs.id"), nullable=False, index=True),
            sa.Column("provider", sa.String(30), nullable=True),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("raw_response", jsonb, nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade():
    op.drop_table("notification_delivery_logs")
    op.drop_table("notification_jobs")
    op.drop_table("notification_preferences")
    op.drop_index("uq_notification_templates_hospital_template_key", table_name="notification_templates")
    op.drop_table("notification_templates")
    op.drop_table("notification_providers")
