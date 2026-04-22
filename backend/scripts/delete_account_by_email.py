"""
Delete a user account and all owned data by email (Postgres or SQLite).
Usage (from repo root, with .env and DATABASE_URL set):
  python backend/scripts/delete_account_by_email.py pureslurp@gmail.com
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Load .env (repo root: parent of `backend/`)
from dotenv import load_dotenv

load_dotenv(_BACKEND_ROOT.parent / ".env", override=True)

# noqa: E402 — env before backend imports
from sqlalchemy.orm import Session

from database import SessionLocal
import models  # register ORM
from models import Account, GoogleOAuthCredential, Project


def delete_account_by_email(db: Session, email: str) -> bool:
    email_norm = email.strip()
    acc = (
        db.query(Account)
        .filter(Account.email.is_not(None), Account.email.ilike(email_norm))
        .first()
    )
    if not acc:
        return False
    # Break project → sale property self-FK so cascades can proceed
    for p in list(acc.projects):
        p.sale_property_id = None
    db.flush()
    for p in list(acc.projects):
        db.delete(p)
    # Flush so rows are removed before we touch accounts (FK: google → accounts)
    db.flush()
    (
        db.query(GoogleOAuthCredential)
        .filter(GoogleOAuthCredential.id == acc.id)
        .delete(synchronize_session=False)
    )
    db.delete(acc)
    db.commit()
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("email", help="Account email to remove (exact match, case-insensitive)")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if delete_account_by_email(db, args.email):
            print(f"Deleted account for {args.email!r} and all owned data.")
            return 0
        print(f"No account with email {args.email!r}.", file=sys.stderr)
        return 1
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
