"""Add gmail_keyword_mode to projects (include vs exclude subject keywords).

Revision ID: 009_gmail_keyword_mode
Revises: 008_stripe_billing
Create Date: 2026-04-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "009_gmail_keyword_mode"
down_revision = "008_stripe_billing"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column(
        "projects",
        sa.Column("gmail_keyword_mode", sa.String(), nullable=False, server_default="include"),
    )


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_column("projects", "gmail_keyword_mode")
