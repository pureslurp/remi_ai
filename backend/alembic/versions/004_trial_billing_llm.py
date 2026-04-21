"""Trial/Pro usage counters, project LLM preferences.

Revision ID: 004_trial_billing
Revises: 003_account_prompts
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004_trial_billing"
down_revision = "003_account_prompts"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column(
        "accounts",
        sa.Column("subscription_tier", sa.String(), nullable=False, server_default="pro"),
    )
    op.add_column("accounts", sa.Column("trial_started_at", sa.DateTime(), nullable=True))
    op.add_column(
        "accounts",
        sa.Column("trial_messages_used", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("accounts", sa.Column("pro_billing_month", sa.String(), nullable=True))
    op.add_column(
        "accounts",
        sa.Column("pro_messages_used", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("projects", sa.Column("llm_provider", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("llm_model", sa.String(), nullable=True))
    op.alter_column("accounts", "subscription_tier", server_default=None)


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_column("projects", "llm_model")
    op.drop_column("projects", "llm_provider")
    op.drop_column("accounts", "pro_messages_used")
    op.drop_column("accounts", "pro_billing_month")
    op.drop_column("accounts", "trial_messages_used")
    op.drop_column("accounts", "trial_started_at")
    op.drop_column("accounts", "subscription_tier")
