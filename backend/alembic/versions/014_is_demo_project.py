"""Add is_demo flag to projects table.

Revision ID: 014_is_demo_project
Revises: 013_property_reapi_id
Create Date: 2026-04-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "014_is_demo_project"
down_revision = "013_property_reapi_id"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column(
        "projects",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_one_demo_per_owner "
        "ON projects (owner_id) WHERE (is_demo = true)"
    )


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_index("idx_projects_one_demo_per_owner", table_name="projects")
    op.drop_column("projects", "is_demo")
