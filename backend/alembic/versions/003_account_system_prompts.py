"""Per-account optional overrides for AI strategy system prompts.

Revision ID: 003_account_prompts
Revises: 002_multi_tenant
Create Date: 2026-04-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003_account_prompts"
down_revision = "002_multi_tenant"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column("accounts", sa.Column("system_prompt_buyer", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("system_prompt_seller", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("system_prompt_buyer_seller", sa.Text(), nullable=True))


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_column("accounts", "system_prompt_buyer_seller")
    op.drop_column("accounts", "system_prompt_seller")
    op.drop_column("accounts", "system_prompt_buyer")
