"""Add surgery module tables (Phase 1 POA)

Revision ID: surgery_tables_012
Revises: sample_order_updated_at_011
Create Date: 2026-02-23

Surgery case, team, documentation, video, and video view audit.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "surgery_tables_012"
down_revision = "sample_order_updated_at_011"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create surgery_cases table only if it does NOT already exist
    if "surgery_cases" not in inspector.get_table_names():
        op.create_table(
            "surgery_cases",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lead_surgeon_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("surgery_name", sa.String(255), nullable=False),
            sa.Column("surgery_type", sa.String(20), nullable=False),
            sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'SCHEDULED'")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
            sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
            sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
            sa.ForeignKeyConstraint(["lead_surgeon_id"], ["users.id"]),
        )
        op.create_index("ix_surgery_cases_hospital_id", "surgery_cases", ["hospital_id"], unique=False)
        op.create_index("ix_surgery_cases_patient_id", "surgery_cases", ["patient_id"], unique=False)
        op.create_index("ix_surgery_cases_admission_id", "surgery_cases", ["admission_id"], unique=False)
        op.create_index("ix_surgery_cases_lead_surgeon_id", "surgery_cases", ["lead_surgeon_id"], unique=False)

    op.create_table(
        "surgery_team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("surgery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
        sa.ForeignKeyConstraint(["surgery_id"], ["surgery_cases.id"]),
        sa.ForeignKeyConstraint(["staff_id"], ["users.id"]),
    )
    op.create_index("ix_surgery_team_members_surgery_id", "surgery_team_members", ["surgery_id"], unique=False)
    op.create_index("ix_surgery_team_members_staff_id", "surgery_team_members", ["staff_id"], unique=False)

    op.create_table(
        "surgery_documentation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("surgery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("procedure_performed", sa.Text(), nullable=False),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("complications", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("post_op_instructions", sa.Text(), nullable=True),
        sa.Column("patient_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
        sa.ForeignKeyConstraint(["surgery_id"], ["surgery_cases.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
    )
    op.create_index("ix_surgery_documentation_surgery_id", "surgery_documentation", ["surgery_id"], unique=False)
    op.create_index("ix_surgery_documentation_patient_id", "surgery_documentation", ["patient_id"], unique=False)

    op.create_table(
        "surgery_videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("surgery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), server_default=sa.text("'video/mp4'"), nullable=True),
        sa.Column("visibility", sa.String(20), nullable=False, server_default=sa.text("'PATIENT_ONLY'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
        sa.ForeignKeyConstraint(["surgery_id"], ["surgery_cases.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
    )
    op.create_index("ix_surgery_videos_surgery_id", "surgery_videos", ["surgery_id"], unique=False)
    op.create_index("ix_surgery_videos_patient_id", "surgery_videos", ["patient_id"], unique=False)

    op.create_table(
        "surgery_video_view_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("surgery_video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("surgery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
        sa.ForeignKeyConstraint(["surgery_video_id"], ["surgery_videos.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"]),
        sa.ForeignKeyConstraint(["surgery_id"], ["surgery_cases.id"]),
    )
    op.create_index("ix_surgery_video_view_audits_surgery_video_id", "surgery_video_view_audits", ["surgery_video_id"], unique=False)
    op.create_index("ix_surgery_video_view_audits_patient_id", "surgery_video_view_audits", ["patient_id"], unique=False)
    op.create_index("ix_surgery_video_view_audits_surgery_id", "surgery_video_view_audits", ["surgery_id"], unique=False)


def downgrade():
    op.drop_table("surgery_video_view_audits")
    op.drop_table("surgery_videos")
    op.drop_table("surgery_documentation")
    op.drop_table("surgery_team_members")
    op.drop_table("surgery_cases")
