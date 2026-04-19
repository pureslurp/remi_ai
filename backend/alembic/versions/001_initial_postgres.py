"""Create all tables on Postgres (Supabase).

Revision ID: 001_initial
Revises:
Create Date: 2026-04-19
"""

from alembic import op
from database import Base
import models  # noqa: F401, E402

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    Base.metadata.drop_all(bind=bind)
