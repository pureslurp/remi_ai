#!/usr/bin/env python3
"""
Copy Reco data from local SQLite (~/.reco/reco.db) into Supabase Postgres.

Uses DATABASE_URL from .env (repo root). Does not upload files under
~/.reco/projects/... — only database rows. Document binaries need Supabase
Storage (or re-upload) separately if you relied on local paths.

Usage (from repo root):
  cd backend && python scripts/sqlite_to_supabase.py
  cd backend && python scripts/sqlite_to_supabase.py --replace
  cd backend && python scripts/sqlite_to_supabase.py --sqlite-path /path/to/reco.db --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent

# FK-safe insert order (parents before children)
TABLE_ORDER = [
    "projects",
    "properties",
    "transactions",
    "key_dates",
    "documents",
    "document_chunks",
    "chat_messages",
    "email_threads",
    "email_messages",
    "google_oauth_credentials",
]


def _json_safe(val):
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, (bytes, memoryview)):
        return val.decode("utf-8", errors="replace")
    if isinstance(val, str):
        s = val.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                pass
    return val


def row_to_dict(columns: list[str], row: tuple) -> dict:
    out = {}
    for col, val in zip(columns, row):
        if col in (
            "email_addresses",
            "gmail_keywords",
            "gmail_address_rules",
            "contingencies",
            "participants",
            "to_addrs",
        ):
            out[col] = _json_safe(val)
        else:
            out[col] = val
    return out


def truncate_target(pc: Connection) -> None:
    pc.execute(text("TRUNCATE TABLE projects CASCADE"))
    pc.execute(text("TRUNCATE TABLE google_oauth_credentials"))


def reflect_table(engine: Engine, name: str) -> Table:
    md = MetaData()
    return Table(name, md, autoload_with=engine)


def copy_tables(
    sqlite_engine: Engine,
    pg_engine: Engine,
    *,
    replace: bool,
    dry_run: bool,
) -> None:
    sins = inspect(sqlite_engine)
    pins = inspect(pg_engine)
    sqlite_tables = set(sins.get_table_names())
    pg_tables = set(pins.get_table_names(schema="public"))
    missing = [t for t in TABLE_ORDER if t not in sqlite_tables]
    if missing:
        print(f"SQLite missing tables (skipped if empty DB): {missing}", file=sys.stderr)
    pg_missing = [t for t in TABLE_ORDER if t not in pg_tables]
    if pg_missing:
        sys.exit(
            f"Postgres missing tables {pg_missing}. Run Alembic migrations on Supabase first."
        )

    with sqlite_engine.connect() as sc, pg_engine.begin() as pc:
        if replace and not dry_run:
            truncate_target(pc)

        total = 0
        for name in TABLE_ORDER:
            if name not in sqlite_tables:
                print(f"  skip {name} (not in SQLite)")
                continue
            st = reflect_table(sqlite_engine, name)
            pt = reflect_table(pg_engine, name)
            cols = [c.name for c in st.columns]
            result = sc.execute(select(*[st.c[c] for c in cols]))
            rows_raw = result.fetchall()
            if not rows_raw:
                print(f"  {name}: 0 rows")
                continue
            rows = [row_to_dict(cols, tuple(r)) for r in rows_raw]
            print(f"  {name}: {len(rows)} rows")
            if dry_run:
                total += len(rows)
                continue
            pk_cols = [c.name for c in pt.primary_key]
            if not pk_cols:
                sys.exit(f"Table {name} has no primary key in Postgres; aborting.")
            stmt = pg_insert(pt).values(rows)
            if not replace:
                stmt = stmt.on_conflict_do_nothing(index_elements=pk_cols)
            pc.execute(stmt)
            total += len(rows)
        if dry_run:
            print(f"dry-run: would copy {total} rows total")
        else:
            print(f"done: wrote {total} row inserts (conflicts ignored unless --replace).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=None,
        help=f"Default: RECO_HOME/reco.db (RECO_HOME default {Path.home() / '.reco'})",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Truncate Reco tables on Postgres then copy (destructive on target).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print row counts; no writes.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    pg_url = os.environ.get("DATABASE_URL", "").strip()
    if not pg_url.split(":", 1)[0].startswith("postgres"):
        sys.exit("Set DATABASE_URL in .env to your Supabase Postgres URL before running.")

    reco_home = Path(
        os.environ.get("RECO_HOME", "").strip()
        or os.environ.get("KOVA_HOME", "").strip()
        or os.environ.get("REMI_HOME", "").strip()
        or str(Path.home() / ".reco")
    )
    # Prefer reco.db, fall back to legacy kova.db or remi.db.
    default_sqlite = reco_home / "reco.db"
    if not default_sqlite.exists():
        for _legacy_name in ("kova.db", "remi.db"):
            _legacy = reco_home / _legacy_name
            if _legacy.exists():
                default_sqlite = _legacy
                break
    sqlite_path = args.sqlite_path or default_sqlite
    if not sqlite_path.is_file():
        sys.exit(f"SQLite file not found: {sqlite_path}")

    sqlite_url = f"sqlite:///{sqlite_path}"
    sqlite_engine = create_engine(
        sqlite_url, connect_args={"check_same_thread": False}
    )
    pg_engine = create_engine(pg_url, pool_pre_ping=True)

    print(f"Source: {sqlite_path}")
    print(f"Target: postgres ({'TRUNCATE + copy' if args.replace else 'merge (skip duplicate PKs)'})")
    copy_tables(sqlite_engine, pg_engine, replace=args.replace, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
