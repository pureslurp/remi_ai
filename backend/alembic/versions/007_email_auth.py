"""Add email/password auth support: auth_provider and password_hash columns.

Revision ID: 007_email_auth
Revises: 006_sale_property
Create Date: 2026-04-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "007_email_auth"
down_revision = "006_sale_property"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column(
        "accounts",
        sa.Column("auth_provider", sa.String(), nullable=False, server_default="google"),
    )
    op.add_column(
        "accounts",
        sa.Column("password_hash", sa.String(), nullable=True),
    )
    op.create_index("uq_accounts_email", "accounts", ["email"], unique=True)


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_index("uq_accounts_email", table_name="accounts")
    op.drop_column("accounts", "password_hash")
    op.drop_column("accounts", "auth_provider")
