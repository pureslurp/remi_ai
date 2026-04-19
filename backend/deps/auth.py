from __future__ import annotations

from typing import Annotated, Generator

from fastapi import Depends, HTTPException, Request

from config import LOCAL_ACCOUNT_ID, SESSION_COOKIE_NAME, is_postgres
from deps import auth_context
from deps.session_jwt import decode_session_token


def require_account(request: Request) -> Generator[str, None, None]:
    """Bind request account id for DB + Google token access; 401 if missing session (Postgres)."""
    if not is_postgres():
        tok = auth_context.bind_request_account_id(LOCAL_ACCOUNT_ID)
        try:
            yield LOCAL_ACCOUNT_ID
        finally:
            auth_context.reset_request_account_id(tok)
        return

    raw = request.cookies.get(SESSION_COOKIE_NAME)
    sub = decode_session_token(raw) if raw else None
    if not sub:
        raise HTTPException(status_code=401, detail="Not authenticated")
    tok = auth_context.bind_request_account_id(sub)
    try:
        yield sub
    finally:
        auth_context.reset_request_account_id(tok)


CurrentAccount = Annotated[str, Depends(require_account)]
