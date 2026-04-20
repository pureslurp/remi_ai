import hmac
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config import (
    CREDENTIALS_PATH,
    FRONTEND_ORIGIN,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_SCOPES,
    LOCAL_ACCOUNT_ID,
    SESSION_COOKIE_NAME,
    SESSION_SECRET,
    SESSION_TTL_DAYS,
    is_postgres,
)
from database import get_db
from deps.auth import require_account
from deps.session_jwt import create_session_token, decode_session_token
from models import Account
from services import google_token_store

# Short-lived cookie that binds the OAuth `state` param to this browser.
# Without this, /api/auth/google/callback accepts any valid Google code+state,
# which lets an attacker log the victim into the attacker's Google account
# (OAuth login CSRF).
_OAUTH_STATE_COOKIE = "remi_oauth_state"
_OAUTH_STATE_TTL_SECONDS = 10 * 60  # 10 min — covers Google consent screen


def _oauth_state_signing_key() -> bytes:
    """Reuse SESSION_SECRET for HMAC if set; otherwise a local-only dev key."""
    if SESSION_SECRET:
        return SESSION_SECRET.encode("utf-8")
    return b"sqlite-dev-oauth-state-key-not-for-production"


def _mint_oauth_state() -> str:
    nonce = secrets.token_urlsafe(24)
    ts = str(int(time.time()))
    mac = hmac.new(
        _oauth_state_signing_key(), f"{nonce}.{ts}".encode(), hashlib.sha256
    ).hexdigest()
    return f"{nonce}.{ts}.{mac}"


def _verify_oauth_state(received: str | None, cookie: str | None) -> bool:
    if not received or not cookie:
        return False
    # Compare in constant time; must match the value we stored in the cookie.
    if not hmac.compare_digest(received, cookie):
        return False
    parts = received.split(".")
    if len(parts) != 3:
        return False
    nonce, ts, mac = parts
    expected = hmac.new(
        _oauth_state_signing_key(), f"{nonce}.{ts}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(mac, expected):
        return False
    try:
        issued = int(ts)
    except ValueError:
        return False
    return (time.time() - issued) <= _OAUTH_STATE_TTL_SECONDS

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _google_user_profile(access_token: str) -> dict:
    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return {}


def _web_client_config() -> dict:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            400,
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET for cloud OAuth, "
            "or place credentials.json at ~/.remi/credentials.json for local use.",
        )
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }


def _get_flow():
    from google_auth_oauthlib.flow import Flow

    if CREDENTIALS_PATH.exists():
        return Flow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            scopes=GOOGLE_SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI,
        )
    return Flow.from_client_config(
        _web_client_config(),
        scopes=GOOGLE_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )


def _upsert_account(db: Session, sub: str, email: str | None, name: str | None, picture: str | None) -> None:
    row = db.get(Account, sub)
    now = datetime.utcnow()
    if row:
        if email:
            row.email = email
        if name:
            row.name = name
        if picture:
            row.picture = picture
        row.updated_at = now
    else:
        db.add(
            Account(
                id=sub,
                email=email,
                name=name,
                picture=picture,
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()


@router.get("/google/url")
def google_auth_url(response: Response):
    try:
        flow = _get_flow()
    except FileNotFoundError:
        raise HTTPException(
            400,
            "credentials.json not found at ~/.remi/credentials.json. "
            "See README for GCP setup, or set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET for web OAuth.",
        )
    state = _mint_oauth_state()
    auth_url, _ = flow.authorization_url(
        access_type="offline", prompt="consent", state=state
    )
    # Browser returns this cookie alongside Google's ?state= on the callback;
    # we require they match so an attacker-initiated code can't finish login.
    response.set_cookie(
        _OAUTH_STATE_COOKIE,
        state,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=_OAUTH_STATE_TTL_SECONDS,
        path="/",
    )
    return {"url": auth_url}


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    if not _verify_oauth_state(state, request.cookies.get(_OAUTH_STATE_COOKIE)):
        raise HTTPException(400, "Invalid or expired OAuth state. Please retry sign-in.")
    flow = _get_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    raw_json = creds.to_json()

    if not is_postgres():
        google_token_store.save_credentials_json_for_account(LOCAL_ACCOUNT_ID, raw_json)
        resp = RedirectResponse(url=f"{FRONTEND_ORIGIN}/?google_connected=1")
        tok = create_session_token(LOCAL_ACCOUNT_ID)
        resp.set_cookie(
            SESSION_COOKIE_NAME,
            tok,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=SESSION_TTL_DAYS * 86400,
            path="/",
        )
        resp.delete_cookie(_OAUTH_STATE_COOKIE, path="/", secure=True, samesite="none")
        return resp

    prof = _google_user_profile(creds.token)
    sub = prof.get("sub")
    if not sub:
        raise HTTPException(400, "Google did not return user id (sub); cannot create session.")
    _upsert_account(db, sub, prof.get("email"), prof.get("name"), prof.get("picture"))
    google_token_store.save_credentials_json_for_account(sub, raw_json)

    resp = RedirectResponse(url=f"{FRONTEND_ORIGIN}/?google_connected=1")
    session_tok = create_session_token(sub)
    resp.set_cookie(
        SESSION_COOKIE_NAME,
        session_tok,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=SESSION_TTL_DAYS * 86400,
        path="/",
    )
    resp.delete_cookie(_OAUTH_STATE_COOKIE, path="/", secure=True, samesite="none")
    return resp


def _google_status_body(request: Request) -> dict:
    from google.auth.transport.requests import Request as GARequest
    from google.oauth2.credentials import Credentials

    if not is_postgres():
        from deps import auth_context

        tok = auth_context.bind_request_account_id(LOCAL_ACCOUNT_ID)
        try:
            if not google_token_store.credentials_exist():
                return {"authenticated": False, "reason": "not_connected"}
            info = google_token_store.credentials_to_info()
            if not info:
                return {"authenticated": False, "reason": "not_connected"}
            creds = Credentials.from_authorized_user_info(info, GOOGLE_SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(GARequest())
                google_token_store.save_credentials_json(creds.to_json())
            if not creds.valid:
                return {"authenticated": False, "reason": "token_expired"}
            prof = _google_user_profile(creds.token)
            return {
                "authenticated": True,
                "email": prof.get("email"),
                "name": prof.get("name"),
                "picture": prof.get("picture"),
            }
        finally:
            auth_context.reset_request_account_id(tok)

    raw = request.cookies.get(SESSION_COOKIE_NAME)
    sub = decode_session_token(raw) if raw else None
    if not sub:
        return {"authenticated": False, "reason": "no_session"}

    from deps import auth_context

    tok = auth_context.bind_request_account_id(sub)
    try:
        if not google_token_store.credentials_exist():
            return {"authenticated": False, "reason": "not_connected"}
        info = google_token_store.credentials_to_info()
        if not info:
            return {"authenticated": False, "reason": "not_connected"}
        creds = Credentials.from_authorized_user_info(info, GOOGLE_SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(GARequest())
            google_token_store.save_credentials_json(creds.to_json())
        if creds.valid:
            prof = _google_user_profile(creds.token)
            return {
                "authenticated": True,
                "email": prof.get("email"),
                "name": prof.get("name"),
                "picture": prof.get("picture"),
            }
        return {"authenticated": False, "reason": "token_expired"}
    except Exception:
        return {"authenticated": False, "reason": "token_invalid"}
    finally:
        auth_context.reset_request_account_id(tok)


@router.get("/google/status")
def google_status(request: Request):
    return _google_status_body(request)


@router.post("/google/disconnect", status_code=204)
def google_disconnect(
    response: Response,
    _account_id: str = Depends(require_account),
):
    google_token_store.clear_credentials()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", secure=True, samesite="none")
    return response
