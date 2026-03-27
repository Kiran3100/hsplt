"""
fix_999 — Merge all divergent migration heads into a single clean head.

This migration has no schema changes — it simply unifies all the branch
heads that accumulated during parallel development, so `alembic upgrade head`
works cleanly without errors about multiple heads.

Revision ID: fix_999_merge_all_heads
Revises: (all current heads listed below)
"""
revision = 'fix_999_merge_all_heads'
down_revision = (
    '067683c1dab3',
    '1915173ccd31',
    '2f04a901a5a1',
    '8b655b51f867',
    'add_is_active_bills_001',
    'add_telemedicine_tables',
    'billing_001',
    'billing_ins_claim_fix_012',
    'billing_ins_prov_015',
    'billing_002',
    'd38c70f097c0',
    'fix_001_idempotency',
    'fix_pm_fk_001',
    'patient_hospital_nullable_001',
    'payment_gw_003',
)
branch_labels = None
depends_on = None


def upgrade():
    """No-op merge — no schema changes."""
    pass


def downgrade():
    pass
