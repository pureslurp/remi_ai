"""Token usage counters on accounts.

Revision ID: 005_token_usage
Revises: 004_trial_billing
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005_token_usage"
down_revision = "004_trial_billing"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column(
        "accounts",
        sa.Column("trial_tokens_used", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "accounts",
        sa.Column("pro_tokens_used", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_column("accounts", "pro_tokens_used")
    op.drop_column("accounts", "trial_tokens_used")
