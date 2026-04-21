"""Project column: sale_property_id for buyer & seller workspace.

Revision ID: 006_sale_property
Revises: 005_token_usage
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "006_sale_property"
down_revision = "005_token_usage"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column("projects", sa.Column("sale_property_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_projects_sale_property_id_properties",
        "projects",
        "properties",
        ["sale_property_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_constraint("fk_projects_sale_property_id_properties", "projects", type_="foreignkey")
    op.drop_column("projects", "sale_property_id")
