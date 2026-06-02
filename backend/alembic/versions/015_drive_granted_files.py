"""Projects: drive_granted_files for drive.file Picker grants.

Revision ID: 015_drive_granted_files
Revises: 014_is_demo_project
Create Date: 2026-06-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "015_drive_granted_files"
down_revision = "014_is_demo_project"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column(
        "projects",
        sa.Column("drive_granted_files", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("projects", sa.Column("drive_folder_resource_key", sa.String(), nullable=True))


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_column("projects", "drive_folder_resource_key")
    op.drop_column("projects", "drive_granted_files")
