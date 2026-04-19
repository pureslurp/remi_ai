from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Request

from config import LOCAL_ACCOUNT_ID, SESSION_COOKIE_NAME, is_postgres
from deps import auth_context
from deps.session_jwt import decode_session_token


async def require_account(request: Request) -> AsyncGenerator[str, None]:
    """Bind request account id for DB + Google token access; 401 if missing session (Postgres).

    MUST be `async def`: FastAPI runs sync `yield` deps inside `run_in_threadpool`,
    which executes in a worker that owns its own ContextVar copy. ContextVar
    mutations there are invisible to the route handler (which runs in a
    different worker copy), so `peek_request_account_id()` would return None
    inside services like `google_token_store`. As an async dep we run in the
    request task's own context and the value propagates correctly into every
    `run_in_threadpool` call FastAPI makes for the handler.
    """
    if not is_postgres():
        prev = auth_context.bind_request_account_id(LOCAL_ACCOUNT_ID)
        request.state.account_id = LOCAL_ACCOUNT_ID
        try:
            yield LOCAL_ACCOUNT_ID
        finally:
            auth_context.reset_request_account_id(prev)
        return

    raw = request.cookies.get(SESSION_COOKIE_NAME)
    sub = decode_session_token(raw) if raw else None
    if not sub:
        raise HTTPException(status_code=401, detail="Not authenticated")
    prev = auth_context.bind_request_account_id(sub)
    request.state.account_id = sub
    try:
        yield sub
    finally:
        auth_context.reset_request_account_id(prev)


CurrentAccount = Annotated[str, Depends(require_account)]
