"""Per-request Google account id (Postgres) or implicit local id (SQLite)."""

from contextvars import ContextVar

_request_account_id: ContextVar[str | None] = ContextVar("request_account_id", default=None)


def bind_request_account_id(account_id: str):
    """Return token for ContextVar.reset."""
    return _request_account_id.set(account_id)


def reset_request_account_id(token) -> None:
    _request_account_id.reset(token)


def peek_request_account_id() -> str | None:
    return _request_account_id.get()
