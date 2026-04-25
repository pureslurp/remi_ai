"""Add subscription_scheduled_plan and subscription_schedule_id to accounts.

Revision ID: 012_billing_scheduled_downgrade
Revises: 011_billing_cancel_at_period_end
Create Date: 2026-04-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "012_billing_scheduled_downgrade"
down_revision = "011_billing_cancel_at_period_end"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column("accounts", sa.Column("subscription_scheduled_plan", sa.String(), nullable=True))
    op.add_column("accounts", sa.Column("subscription_schedule_id", sa.String(), nullable=True))


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_column("accounts", "subscription_schedule_id")
    op.drop_column("accounts", "subscription_scheduled_plan")
