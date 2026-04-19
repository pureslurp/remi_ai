"""Accounts, project ownership, per-user Google OAuth.

Revision ID: 002_multi_tenant
Revises: 001_initial
Create Date: 2026-04-19
"""

from __future__ import annotations

import base64
import json

import sqlalchemy as sa
from alembic import op

revision = "002_multi_tenant"
down_revision = "001_initial"
branch_labels = None
depends_on = None

LEGACY_ACCOUNT_ID = "legacy"


def _sub_from_id_token(id_token: str) -> str | None:
    try:
        parts = id_token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("sub")
    except Exception:
        return None


def _sub_from_credentials_json(raw: str) -> str | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    id_tok = data.get("id_token")
    if id_tok:
        return _sub_from_id_token(id_tok)
    return None


def _fk_names(conn, table: str) -> set[str]:
    insp = sa.inspect(conn)
    return {fk.get("name") for fk in insp.get_foreign_keys(table) if fk.get("name")}


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    if "accounts" not in tables:
        op.create_table(
            "accounts",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("picture", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    insp = sa.inspect(conn)
    proj_cols = {c["name"] for c in insp.get_columns("projects")}
    if "owner_id" not in proj_cols:
        op.add_column("projects", sa.Column("owner_id", sa.String(), nullable=True))

    conn.execute(
        sa.text(
            """
            INSERT INTO accounts (id, email, name, picture, created_at, updated_at)
            VALUES (:id, :email, NULL, NULL, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": LEGACY_ACCOUNT_ID, "email": "legacy@local"},
    )

    account_id = LEGACY_ACCOUNT_ID
    row = conn.execute(
        sa.text("SELECT id, credentials_json FROM google_oauth_credentials WHERE id = 'default'")
    ).fetchone()
    if row and row[1]:
        parsed = _sub_from_credentials_json(row[1])
        if parsed:
            account_id = parsed
            conn.execute(
                sa.text(
                    """
                    INSERT INTO accounts (id, email, name, picture, created_at, updated_at)
                    VALUES (:id, NULL, NULL, NULL, NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": account_id},
            )

    conn.execute(sa.text("UPDATE projects SET owner_id = :aid WHERE owner_id IS NULL"), {"aid": account_id})

    if row:
        conn.execute(sa.text("DELETE FROM google_oauth_credentials WHERE id = 'default'"))
        conn.execute(
            sa.text(
                """
                INSERT INTO google_oauth_credentials (id, credentials_json)
                VALUES (:id, :json)
                ON CONFLICT (id) DO UPDATE SET credentials_json = EXCLUDED.credentials_json
                """
            ),
            {"id": account_id, "json": row[1]},
        )

    op.alter_column("projects", "owner_id", nullable=False)

    if "fk_projects_owner_id_accounts" not in _fk_names(conn, "projects"):
        op.create_foreign_key(
            "fk_projects_owner_id_accounts",
            "projects",
            "accounts",
            ["owner_id"],
            ["id"],
        )

    if "fk_google_oauth_account" not in _fk_names(conn, "google_oauth_credentials"):
        op.create_foreign_key(
            "fk_google_oauth_account",
            "google_oauth_credentials",
            "accounts",
            ["id"],
            ["id"],
        )


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    for name, table in [
        ("fk_google_oauth_account", "google_oauth_credentials"),
        ("fk_projects_owner_id_accounts", "projects"),
    ]:
        if name in _fk_names(conn, table):
            op.drop_constraint(name, table, type_="foreignkey")
    op.drop_column("projects", "owner_id")
    op.drop_table("accounts")
