"""merge_billing_and_is_active_heads

Revision ID: 2f04a901a5a1
Revises: add_is_active_bills_001, billing_003
Create Date: 2026-02-24 16:13:40.935076

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f04a901a5a1'
down_revision = ('add_is_active_bills_001', 'billing_003')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass