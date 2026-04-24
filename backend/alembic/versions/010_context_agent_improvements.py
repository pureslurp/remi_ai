"""Context agent: document summary, email thread tags, chat references, conversation summary.

Revision ID: 010_context_agent
Revises: 009_gmail_keyword_mode
Create Date: 2026-04-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "010_context_agent"
down_revision = "009_gmail_keyword_mode"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.add_column("documents", sa.Column("short_summary", sa.Text(), nullable=True))
    op.add_column("email_threads", sa.Column("transaction_id", sa.String(), nullable=True))
    op.add_column("email_threads", sa.Column("tag_source", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_email_threads_transaction",
        "email_threads",
        "transactions",
        ["transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("chat_messages", sa.Column("referenced_items", sa.JSON(), nullable=True))
    op.create_table(
        "project_conversation_summaries",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("covered_message_id", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["covered_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.alter_column(
        "project_conversation_summaries", "summary_text", server_default=None, existing_type=sa.Text()
    )


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_table("project_conversation_summaries")
    op.drop_column("chat_messages", "referenced_items")
    op.drop_constraint("fk_email_threads_transaction", "email_threads", type_="foreignkey")
    op.drop_column("email_threads", "tag_source")
    op.drop_column("email_threads", "transaction_id")
    op.drop_column("documents", "short_summary")
