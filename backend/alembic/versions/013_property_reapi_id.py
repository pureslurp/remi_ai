"""Properties: optional reapi_property_id (vendor id cache).

Revision ID: 013_property_reapi_id
Revises: 012_billing_scheduled_downgrade
Create Date: 2026-04-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "013_property_reapi_id"
down_revision = "012_billing_scheduled_downgrade"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column("properties", sa.Column("reapi_property_id", sa.String(), nullable=True))


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_column("properties", "reapi_property_id")
