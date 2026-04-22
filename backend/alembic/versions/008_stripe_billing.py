"""Add Stripe billing columns to accounts.

Revision ID: 008_stripe_billing
Revises: 007_email_auth
Create Date: 2026-04-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "008_stripe_billing"
down_revision = "007_email_auth"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column("accounts", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.add_column("accounts", sa.Column("stripe_subscription_id", sa.String(), nullable=True))
    op.add_column("accounts", sa.Column("subscription_status", sa.String(), nullable=True))
    op.add_column("accounts", sa.Column("subscription_current_period_end", sa.DateTime(), nullable=True))
    # Index for fast webhook lookups by Stripe customer ID
    op.create_index("ix_accounts_stripe_customer_id", "accounts", ["stripe_customer_id"], unique=False)


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_index("ix_accounts_stripe_customer_id", table_name="accounts")
    op.drop_column("accounts", "subscription_current_period_end")
    op.drop_column("accounts", "subscription_status")
    op.drop_column("accounts", "stripe_subscription_id")
    op.drop_column("accounts", "stripe_customer_id")
