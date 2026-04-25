"""Add subscription_cancel_at_period_end to accounts.

Revision ID: 011_billing_cancel_at_period_end
Revises: 010_context_agent
Create Date: 2026-04-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "011_billing_cancel_at_period_end"
down_revision = "010_context_agent"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column(
        "accounts",
        sa.Column("subscription_cancel_at_period_end", sa.Boolean(), nullable=True, server_default="false"),
    )


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_column("accounts", "subscription_cancel_at_period_end")
