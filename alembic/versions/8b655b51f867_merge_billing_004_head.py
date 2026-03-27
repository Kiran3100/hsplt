"""merge_billing_004_head

Revision ID: 8b655b51f867
Revises: 2f04a901a5a1, billing_004
Create Date: 2026-02-24 16:24:11.773150

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8b655b51f867'
down_revision = ('2f04a901a5a1', 'billing_004')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass