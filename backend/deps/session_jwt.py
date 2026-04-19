from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from config import SESSION_SECRET, SESSION_TTL_DAYS, is_postgres


def _signing_key() -> str:
    if SESSION_SECRET:
        return SESSION_SECRET
    if not is_postgres():
        return "sqlite-dev-session-secret-not-for-production"
    raise RuntimeError("SESSION_SECRET is required when using Postgres")


def create_session_token(account_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": account_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=SESSION_TTL_DAYS)).timestamp()),
    }
    return jwt.encode(payload, _signing_key(), algorithm="HS256")


def decode_session_token(token: str) -> str | None:
    try:
        data = jwt.decode(token, _signing_key(), algorithms=["HS256"])
        sub = data.get("sub")
        return str(sub) if sub else None
    except jwt.PyJWTError:
        return None
