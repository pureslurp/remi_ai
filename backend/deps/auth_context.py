"""Per-request Google account id (Postgres) or implicit local id (SQLite).

We deliberately do NOT use the ContextVar.Token reset mechanism. FastAPI sync
`yield` dependencies bind the value in the threadpool worker context, but the
generator's `finally` cleanup runs after the route handler in a different
context — `reset(token)` then raises `ValueError: <Token ...> was created in
a different Context` and crashes the request. Manual save/restore via plain
`set()` works regardless of which context runs the cleanup.
"""

from contextvars import ContextVar

_request_account_id: ContextVar[str | None] = ContextVar("request_account_id", default=None)


def bind_request_account_id(account_id: str) -> str | None:
    """Set current account id; return previous value so caller can restore it."""
    prev = _request_account_id.get()
    _request_account_id.set(account_id)
    return prev


def reset_request_account_id(prev: str | None) -> None:
    """Restore the previous value captured by bind_request_account_id."""
    _request_account_id.set(prev)


def peek_request_account_id() -> str | None:
    return _request_account_id.get()
