"""Persist Google OAuth user credentials to file (SQLite/local) or Postgres."""

from __future__ import annotations

import json
from typing import Optional

from config import TOKEN_PATH, is_postgres
from database import SessionLocal
from models import GoogleOAuthCredential

SINGLETON_ID = "default"


def _use_database() -> bool:
    return is_postgres()


def load_credentials_json() -> Optional[str]:
    if _use_database():
        db = SessionLocal()
        try:
            row = db.get(GoogleOAuthCredential, SINGLETON_ID)
            return row.credentials_json if row else None
        finally:
            db.close()
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text(encoding="utf-8")
    return None


def save_credentials_json(data: str) -> None:
    if _use_database():
        db = SessionLocal()
        try:
            row = db.get(GoogleOAuthCredential, SINGLETON_ID)
            if row:
                row.credentials_json = data
            else:
                db.add(GoogleOAuthCredential(id=SINGLETON_ID, credentials_json=data))
            db.commit()
        finally:
            db.close()
    else:
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(data, encoding="utf-8")


def credentials_exist() -> bool:
    if _use_database():
        db = SessionLocal()
        try:
            return db.get(GoogleOAuthCredential, SINGLETON_ID) is not None
        finally:
            db.close()
    return TOKEN_PATH.exists()


def clear_credentials() -> None:
    if _use_database():
        db = SessionLocal()
        try:
            row = db.get(GoogleOAuthCredential, SINGLETON_ID)
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
