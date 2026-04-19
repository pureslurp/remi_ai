"""Persist Google OAuth credentials: per-account on Postgres, single file on SQLite."""

from __future__ import annotations

import json
from typing import Optional

from config import LOCAL_ACCOUNT_ID, TOKEN_PATH, is_postgres
from database import SessionLocal
from deps import auth_context
from models import GoogleOAuthCredential


def _account_id() -> str:
    aid = auth_context.peek_request_account_id()
    if aid:
        return aid
    if not is_postgres():
        return LOCAL_ACCOUNT_ID
    raise RuntimeError("No account context for Google token store")


def load_credentials_json() -> Optional[str]:
    aid = _account_id()
    if is_postgres():
        db = SessionLocal()
        try:
            row = db.get(GoogleOAuthCredential, aid)
            return row.credentials_json if row else None
        finally:
            db.close()
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text(encoding="utf-8")
    return None


def save_credentials_json(data: str) -> None:
    aid = _account_id()
    if is_postgres():
        db = SessionLocal()
        try:
            row = db.get(GoogleOAuthCredential, aid)
            if row:
                row.credentials_json = data
            else:
                db.add(GoogleOAuthCredential(id=aid, credentials_json=data))
            db.commit()
        finally:
            db.close()
    else:
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(data, encoding="utf-8")


def credentials_exist() -> bool:
    aid = _account_id()
    if is_postgres():
        db = SessionLocal()
        try:
            return db.get(GoogleOAuthCredential, aid) is not None
        finally:
            db.close()
    return TOKEN_PATH.exists()


def clear_credentials() -> None:
    aid = _account_id()
    if is_postgres():
        db = SessionLocal()
        try:
            row = db.get(GoogleOAuthCredential, aid)
            if row:
                db.delete(row)
                db.commit()
        finally:
            db.close()
    elif TOKEN_PATH.exists():
        TOKEN_PATH.unlink()


def credentials_to_info() -> Optional[dict]:
    raw = load_credentials_json()
    if not raw:
        return None
    return json.loads(raw)


def save_credentials_json_for_account(account_id: str, data: str) -> None:
    """Save OAuth JSON for `account_id` without request context (OAuth callback only)."""
    if is_postgres():
        db = SessionLocal()
        try:
            row = db.get(GoogleOAuthCredential, account_id)
            if row:
                row.credentials_json = data
            else:
                db.add(GoogleOAuthCredential(id=account_id, credentials_json=data))
            db.commit()
        finally:
            db.close()
    else:
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(data, encoding="utf-8")
