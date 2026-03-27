"""merge_all_billing_heads

Revision ID: 1915173ccd31
Revises: 8b655b51f867, billing_005
Create Date: 2026-02-24 16:56:43.270094

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1915173ccd31'
down_revision = ('8b655b51f867', 'billing_005')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass