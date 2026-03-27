"""billing_accounts_001 - Billing & Accounts module tables

Revision ID: billing_001
Revises: prescription_notif_001
Create Date: Billing & Accounts (service_items, tax_profiles, bills, bill_items, ipd_charges, payments, financial_documents, insurance_claims, reconciliations, finance_audit_logs)

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = "billing_001"
down_revision = "prescription_notif_001"
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    from sqlalchemy import inspect
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, "tax_profiles"):
        op.create_table(
            "tax_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("gst_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not _table_exists(conn, "service_items"):
        op.create_table(
            "service_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id"), nullable=True),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("base_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("tax_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tax_profiles.id"), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("uq_service_items_hospital_code", "service_items", ["hospital_id", "code"], unique=True)
    if not _table_exists(conn, "bills"):
        op.create_table(
            "bills",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("bill_number", sa.String(50), nullable=False),
            sa.Column("bill_type", sa.String(10), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient_profiles.id"), nullable=False),
            sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id"), nullable=True),
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admissions.id"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
            sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("balance_due", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("finalized_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("discount_approval_required", sa.Boolean(), server_default="false"),
            sa.Column("discount_approved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("uq_bills_hospital_bill_number", "bills", ["hospital_id", "bill_number"], unique=True)
    if not _table_exists(conn, "bill_items"):
        op.create_table(
            "bill_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id"), nullable=False),
            sa.Column("service_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("service_items.id"), nullable=True),
            sa.Column("description", sa.String(500), nullable=False),
            sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
            sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
            sa.Column("tax_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("line_subtotal", sa.Numeric(12, 2), nullable=False),
            sa.Column("line_tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not _table_exists(conn, "ipd_charges"):
        op.create_table(
            "ipd_charges",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id"), nullable=False),
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admissions.id"), nullable=False),
            sa.Column("charge_date", sa.Date(), nullable=False),
            sa.Column("charge_type", sa.String(30), nullable=False),
            sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not _table_exists(conn, "payments"):
        op.create_table(
            "payments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id"), nullable=False),
            sa.Column("payment_ref", sa.String(100), nullable=False),
            sa.Column("method", sa.String(30), nullable=False),
            sa.Column("provider", sa.String(50), nullable=True),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="INITIATED"),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("collected_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("gateway_transaction_id", sa.String(255), nullable=True),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("uq_payments_payment_ref", "payments", ["payment_ref"], unique=True)
    if not _table_exists(conn, "financial_documents"):
        op.create_table(
            "financial_documents",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id"), nullable=True),
            sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id"), nullable=True),
            sa.Column("doc_type", sa.String(20), nullable=False),
            sa.Column("doc_number", sa.String(50), nullable=False),
            sa.Column("pdf_path", sa.String(500), nullable=True),
            sa.Column("emailed_to", sa.String(255), nullable=True),
            sa.Column("template_version", sa.String(50), nullable=True),
            sa.Column("is_duplicate_copy", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("uq_financial_documents_hospital_doc_number", "financial_documents", ["hospital_id", "doc_number"], unique=True)
    if not _table_exists(conn, "insurance_claims"):
        op.create_table(
            "insurance_claims",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id"), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient_profiles.id"), nullable=False),
            sa.Column("insurance_provider_name", sa.String(255), nullable=False),
            sa.Column("policy_number", sa.String(100), nullable=True),
            sa.Column("claim_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("approved_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="CREATED"),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("settlement_reference", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not _table_exists(conn, "reconciliations"):
        op.create_table(
            "reconciliations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("recon_date", sa.Date(), nullable=False),
            sa.Column("total_cash", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("total_card", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("total_upi", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("total_online", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("gateway_report_total", sa.Numeric(12, 2), nullable=True),
            sa.Column("discrepancy_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="OK"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not _table_exists(conn, "finance_audit_logs"):
        op.create_table(
            "finance_audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("hospital_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False, index=True),
            sa.Column("entity_type", sa.String(20), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("action", sa.String(30), nullable=False),
            sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("performed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade():
    op.drop_table("finance_audit_logs")
    op.drop_table("reconciliations")
    op.drop_table("insurance_claims")
    op.drop_table("financial_documents")
    op.drop_table("payments")
    op.drop_table("ipd_charges")
    op.drop_table("bill_items")
    op.drop_table("bills")
    op.drop_table("service_items")
    op.drop_table("tax_profiles")
