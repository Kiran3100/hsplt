"""
fix_001 — Add payment_idempotency_keys table and clinical_access_audit_log table.

Revision ID: fix_001_idempotency
Revises: (set to current head in your environment)
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa

# Note: set `down_revision` to the current head revision in your alembic chain.
revision = 'fix_001_idempotency'
down_revision = None  # Set this to your current head revision
branch_labels = None
depends_on = None


def upgrade():
    # ── Payment Idempotency Keys ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS payment_idempotency_keys (
            key         VARCHAR(255) PRIMARY KEY,
            hospital_id UUID         NOT NULL,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            expires_at  TIMESTAMPTZ  NOT NULL
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_idempotency_hospital
        ON payment_idempotency_keys(hospital_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_idempotency_expires
        ON payment_idempotency_keys(expires_at)
    """)

    # ── Clinical Access Audit Log ─────────────────────────────────────────────
    # Records every access to patient records for HIPAA compliance.
    op.execute("""
        CREATE TABLE IF NOT EXISTS clinical_access_audit_log (
            id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            hospital_id  UUID         NOT NULL,
            accessed_by  UUID         NOT NULL,
            patient_id   UUID,
            resource     VARCHAR(100) NOT NULL,
            action       VARCHAR(50)  NOT NULL,
            ip_address   VARCHAR(45),
            user_agent   VARCHAR(500),
            accessed_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_clinical_audit_hospital
        ON clinical_access_audit_log(hospital_id, accessed_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_clinical_audit_patient
        ON clinical_access_audit_log(patient_id, accessed_at DESC)
    """)

    # ── Unique constraint on appointments to prevent double booking ──────────
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_appointment_doctor_datetime
        ON appointments(doctor_id, appointment_date, appointment_time)
        WHERE status NOT IN ('CANCELLED', 'NO_SHOW')
    """)

    # ── TOTP secrets for 2FA ──────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret      VARCHAR(64);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled     BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_verified_at TIMESTAMPTZ;
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS payment_idempotency_keys")
    op.execute("DROP TABLE IF EXISTS clinical_access_audit_log")
    op.execute("DROP INDEX IF EXISTS uq_appointment_doctor_datetime")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS totp_secret")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS totp_enabled")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS totp_verified_at")
