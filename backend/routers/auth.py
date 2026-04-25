import hmac
import hashlib
import json
import logging
import os
import re
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
import bcrypt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import (
    CREDENTIALS_PATH,
    FRONTEND_ORIGIN,
    POST_GOOGLE_OAUTH_FRONTEND_ORIGIN,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_SCOPES,
    LOCAL_ACCOUNT_ID,
    SESSION_COOKIE_NAME,
    SESSION_SECRET,
    SESSION_TTL_DAYS,
    is_postgres,
    postgres_connection_diagnostics,
)
from database import get_db
from deps.auth import require_account
from deps.session_jwt import create_session_token, decode_session_token
from models import Account
from models.google_oauth import GoogleOAuthCredential
from services import google_token_store
from services.usage_entitlements import default_subscription_tier_for_new_account

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Consumer Gmail must use Google OAuth (Gmail/Drive sync, correct identity). Workspace
# domains (anything not @gmail.com / @googlemail.com) may still use email/password.
_CONSUMER_GMAIL_EMAIL_AUTH_MSG = (
    "Gmail addresses must use Continue with Google. "
    "Email and password sign-up and sign-in are not available for @gmail.com or @googlemail.com."
)


def _is_consumer_gmail_address(email: str) -> bool:
    raw = email.strip().lower()
    if "@" not in raw:
        return False
    domain = raw.rsplit("@", 1)[-1]
    return domain in ("gmail.com", "googlemail.com")


logger = logging.getLogger("reco.auth")

# Short-lived cookie that binds the OAuth `state` param to this browser.
# Without this, /api/auth/google/callback accepts any valid Google code+state,
# which lets an attacker log the victim into the attacker's Google account
# (OAuth login CSRF).
_OAUTH_STATE_COOKIE = "reco_oauth_state"
_OAUTH_STATE_TTL_SECONDS = 10 * 60  # 10 min — covers Google consent screen


def _cookie_transport(request: Request) -> tuple[bool, str]:
    """(secure, samesite). HTTP cannot use Secure or SameSite=None — browsers reject them."""
    if request.url.scheme == "https":
        return True, "none"
    return False, "lax"


def _auth_debug_enabled() -> bool:
    """Rich JSON errors + /diagnostics. RECO_AUTH_DEBUG=1 or RECO_DEBUG / REMIP_DEBUG."""
    for key in ("RECO_AUTH_DEBUG", "RECO_DEBUG", "KOVA_AUTH_DEBUG", "KOVA_DEBUG", "REMIP_DEBUG"):
        v = os.environ.get(key, "").strip().lower()
        if v in ("1", "true", "yes"):
            return True
    return False


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


def _check_oauth_state(received: str | None, cookie: str | None) -> tuple[bool, str]:
    """Return (ok, reason_code) for logging and debug responses — no secrets."""
    if not received:
        return False, "missing_state_query"
    if not cookie:
        return False, "missing_oauth_state_cookie"
    # Compare in constant time; must match the value we stored in the cookie.
    if not hmac.compare_digest(received, cookie):
        return False, "state_query_cookie_mismatch"
    # Strip linking prefix before HMAC validation
    raw = received.removeprefix(_LINKING_PREFIX) if received.startswith(_LINKING_PREFIX) else received
    parts = raw.split(".")
    if len(parts) != 3:
        return False, "state_malformed"
    nonce, ts, mac = parts
    expected = hmac.new(
        _oauth_state_signing_key(), f"{nonce}.{ts}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(mac, expected):
        return False, "state_hmac_invalid"
    try:
        issued = int(ts)
    except ValueError:
        return False, "state_timestamp_invalid"
    if (time.time() - issued) > _OAUTH_STATE_TTL_SECONDS:
        return False, "state_expired"
    return True, "ok"


def _verify_oauth_state(received: str | None, cookie: str | None) -> bool:
    ok, _ = _check_oauth_state(received, cookie)
    return ok


router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Pydantic request bodies for email auth
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------------------
# Email auth helpers
# ---------------------------------------------------------------------------

_LINKING_PREFIX = "link."  # prepended to state nonce when linking Google


def _set_session_cookie(response: Response, request: Request, account_id: str) -> None:
    """Create a session JWT and set it as an HttpOnly cookie."""
    tok = create_session_token(account_id)
    _sec, _ss = _cookie_transport(request)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        tok,
        httponly=True,
        secure=_sec,
        samesite=_ss,
        max_age=SESSION_TTL_DAYS * 86400,
        path="/",
    )


# ---------------------------------------------------------------------------
# POST /api/auth/signup
# ---------------------------------------------------------------------------


@router.post("/signup")
def email_signup(body: SignupRequest, request: Request, db: Session = Depends(get_db)):
    if not _EMAIL_RE.match(body.email):
        raise HTTPException(400, "Invalid email address.")
    if _is_consumer_gmail_address(body.email):
        raise HTTPException(400, _CONSUMER_GMAIL_EMAIL_AUTH_MSG)
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    existing = db.query(Account).filter(Account.email == body.email).first()
    if existing:
        if existing.auth_provider == "google":
            raise HTTPException(
                409,
                "An account with this email exists via Google. Please sign in with Google.",
            )
        raise HTTPException(409, "Account already exists. Try signing in.")

    account_id = str(uuid4())
    now = datetime.utcnow()
    db.add(
        Account(
            id=account_id,
            email=body.email,
            name=body.name,
            auth_provider="email",
            password_hash=bcrypt.hashpw(
                body.password.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8"),
            subscription_tier=default_subscription_tier_for_new_account(account_id),
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    resp = JSONResponse(
        content={
            "authenticated": True,
            "email": body.email,
            "name": body.name,
            "google_connected": False,
        }
    )
    _set_session_cookie(resp, request, account_id)
    return resp


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


@router.post("/login")
def email_login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    if _is_consumer_gmail_address(body.email):
        raise HTTPException(400, _CONSUMER_GMAIL_EMAIL_AUTH_MSG)
    account = db.query(Account).filter(Account.email == body.email).first()
    if not account:
        raise HTTPException(401, "Invalid email or password.")
    if not account.password_hash:
        raise HTTPException(
            401,
            "This email is registered with Google. Use Continue with Google to sign in.",
        )
    try:
        pwd_ok = bcrypt.checkpw(
            body.password.encode("utf-8"),
            account.password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        pwd_ok = False
    if not pwd_ok:
        raise HTTPException(401, "Invalid email or password.")

    google_connected = (
        db.query(GoogleOAuthCredential).filter(GoogleOAuthCredential.id == account.id).first() is not None
    )

    resp = JSONResponse(
        content={
            "authenticated": True,
            "email": account.email,
            "name": account.name,
            "picture": account.picture,
            "google_connected": google_connected,
        }
    )
    _set_session_cookie(resp, request, account.id)
    return resp


# ---------------------------------------------------------------------------
# GET /api/auth/session
# ---------------------------------------------------------------------------


@router.get("/session")
def get_session(request: Request, db: Session = Depends(get_db)):
    raw = request.cookies.get(SESSION_COOKIE_NAME)
    sub = decode_session_token(raw) if raw else None
    if not sub:
        return {"authenticated": False}

    account = db.get(Account, sub)
    if not account:
        return {"authenticated": False}

    google_connected = (
        db.query(GoogleOAuthCredential).filter(GoogleOAuthCredential.id == account.id).first() is not None
    )

    from services.usage_entitlements import subscription_tier as _sub_tier
    return {
        "authenticated": True,
        "account": {
            "email": account.email,
            "name": account.name,
            "picture": account.picture,
            "auth_provider": getattr(account, "auth_provider", "google"),
            "subscription_tier": _sub_tier(account),
            "stripe_customer_id": getattr(account, "stripe_customer_id", None),
        },
        "google_connected": google_connected,
    }


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout")
def logout(request: Request):
    _sec, _ss = _cookie_transport(request)
    # Build the response directly so status_code is set and Set-Cookie is emitted.
    # Returning the FastAPI-injected `response: Response` fixture sends status=None
    # and uvicorn crashes with KeyError before the cookie delete header is flushed.
    resp = Response(status_code=204)
    # Must match set_cookie (httponly/secure/samesite/path) or browsers keep the session cookie.
    resp.delete_cookie(
        SESSION_COOKIE_NAME, path="/", secure=_sec, samesite=_ss, httponly=True
    )
    return resp


# ---------------------------------------------------------------------------
# GET /api/auth/google/link  (for email users to connect Google)
# ---------------------------------------------------------------------------


@router.get("/google/link")
def google_link_url(
    request: Request,
    response: Response,
    _account_id: str = Depends(require_account),
):
    """Generate a Google OAuth URL for linking Google to an existing email account."""
    try:
        flow = _get_flow()
    except FileNotFoundError:
        raise HTTPException(400, "Google OAuth not configured.")

    # Embed linking flag in the state nonce so the callback knows this is a link, not a sign-in.
    state = _LINKING_PREFIX + _mint_oauth_state()
    auth_url, _ = flow.authorization_url(
        access_type="offline", prompt="consent", state=state
    )
    _sec, _ss = _cookie_transport(request)
    response.set_cookie(
        _OAUTH_STATE_COOKIE,
        state,
        httponly=True,
        secure=_sec,
        samesite=_ss,
        max_age=_OAUTH_STATE_TTL_SECONDS,
        path="/",
    )
    return {"url": auth_url}


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
            "or place credentials.json at ~/.reco/credentials.json for local use.",
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
                subscription_tier=default_subscription_tier_for_new_account(sub),
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()


@router.get("/google/url")
def google_auth_url(request: Request, response: Response):
    try:
        flow = _get_flow()
    except FileNotFoundError:
        raise HTTPException(
            400,
            "credentials.json not found at ~/.reco/credentials.json. "
            "See README for GCP setup, or set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET for web OAuth.",
        )
    state = _mint_oauth_state()
    auth_url, _ = flow.authorization_url(
        access_type="offline", prompt="consent", state=state
    )
    # Browser returns this cookie alongside Google's ?state= on the callback;
    # we require they match so an attacker-initiated code can't finish login.
    _sec, _ss = _cookie_transport(request)
    response.set_cookie(
        _OAUTH_STATE_COOKIE,
        state,
        httponly=True,
        secure=_sec,
        samesite=_ss,
        max_age=_OAUTH_STATE_TTL_SECONDS,
        path="/",
    )
    if _auth_debug_enabled():
        logger.info(
            "google_auth_url: redirect_uri=%s cookie_secure=%s samesite=%s",
            GOOGLE_REDIRECT_URI,
            _sec,
            _ss,
        )
    return {"url": auth_url}


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    dbg = _auth_debug_enabled()
    ch = request.headers.get("cookie") or ""
    logger.info(
        "oauth callback: host=%s scheme=%s path=%s x_forwarded_proto=%s "
        "cookie_header_bytes=%s has_%s=%s",
        request.url.hostname,
        request.url.scheme,
        request.url.path,
        request.headers.get("x-forwarded-proto"),
        len(ch.encode("utf-8")),
        _OAUTH_STATE_COOKIE,
        _OAUTH_STATE_COOKIE in request.cookies,
    )

    raw_oauth_cookie = request.cookies.get(_OAUTH_STATE_COOKIE)
    ok, state_reason = _check_oauth_state(state, raw_oauth_cookie)
    if not ok:
        logger.warning("oauth state rejected: %s", state_reason)
        if dbg:
            return JSONResponse(
                status_code=400,
                content={
                    "step": "oauth_state",
                    "reason": state_reason,
                    "GOOGLE_REDIRECT_URI": GOOGLE_REDIRECT_URI,
                    "FRONTEND_ORIGIN": FRONTEND_ORIGIN,
                    "POST_GOOGLE_OAUTH_FRONTEND_ORIGIN": POST_GOOGLE_OAUTH_FRONTEND_ORIGIN,
                    "hint": "GCP 'Authorized redirect URIs' must match GOOGLE_REDIRECT_URI. "
                    "Use Connect Google from the same browser session; if you opened /url on a "
                    "different origin/port than this callback, the state cookie will not match.",
                },
            )
        raise HTTPException(
            400,
            "Invalid or expired OAuth state. Please retry sign-in.",
        )

    try:
        flow = _get_flow()
    except FileNotFoundError:
        logger.error("OAuth flow: credentials.json missing at %s", CREDENTIALS_PATH)
        if dbg:
            return JSONResponse(
                status_code=400,
                content={
                    "step": "credentials_file",
                    "path": str(CREDENTIALS_PATH),
                    "hint": "Add credentials.json or set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET.",
                },
            )
        raise HTTPException(
            400,
            "credentials.json not found. See README for GCP setup.",
        ) from None

    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        logger.exception("oauth fetch_token failed")
        if dbg:
            return JSONResponse(
                status_code=502,
                content={
                    "step": "fetch_token",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "GOOGLE_REDIRECT_URI": GOOGLE_REDIRECT_URI,
                    "hint": "Often redirect_uri mismatch vs GCP, or code already used/expired.",
                },
            )
        raise HTTPException(
            400,
            "Google token exchange failed. Retry sign-in from the app.",
        ) from exc

    creds = flow.credentials
    raw_json = creds.to_json()

    _sec, _ss = _cookie_transport(request)

    if not is_postgres():
        google_token_store.save_credentials_json_for_account(LOCAL_ACCOUNT_ID, raw_json)
        resp = RedirectResponse(
            url=f"{POST_GOOGLE_OAUTH_FRONTEND_ORIGIN}/?google_connected=1"
        )
        tok = create_session_token(LOCAL_ACCOUNT_ID)
        resp.set_cookie(
            SESSION_COOKIE_NAME,
            tok,
            httponly=True,
            secure=_sec,
            samesite=_ss,
            max_age=SESSION_TTL_DAYS * 86400,
            path="/",
        )
        resp.delete_cookie(
            _OAUTH_STATE_COOKIE, path="/", secure=_sec, samesite=_ss, httponly=True
        )
        logger.info("oauth callback ok (sqlite local account)")
        return resp

    prof = _google_user_profile(creds.token)
    sub = prof.get("sub")
    if not sub:
        logger.warning("google userinfo missing sub")
        if dbg:
            return JSONResponse(
                status_code=400,
                content={"step": "userinfo", "profile_keys": list(prof.keys())},
            )
        raise HTTPException(
            400,
            "Google did not return user id (sub); cannot create session.",
        )

    # --- Linking mode: attach Google creds to the currently signed-in email account ---
    is_linking = bool(state and state.startswith(_LINKING_PREFIX))
    if is_linking:
        raw_session = request.cookies.get(SESSION_COOKIE_NAME)
        current_account_id = decode_session_token(raw_session) if raw_session else None
        if not current_account_id:
            raise HTTPException(400, "No active session — cannot link Google. Please sign in first.")

        try:
            google_token_store.save_credentials_json_for_account(current_account_id, raw_json)
        except Exception as exc:
            logger.exception("oauth link save_credentials failed")
            raise HTTPException(500, "Could not store Google credentials.") from exc

        # Update profile picture from Google
        account = db.get(Account, current_account_id)
        if account and prof.get("picture"):
            account.picture = prof["picture"]
            account.updated_at = datetime.utcnow()
            db.commit()

        resp = RedirectResponse(
            url=f"{POST_GOOGLE_OAUTH_FRONTEND_ORIGIN}/?google_linked=1"
        )
        resp.delete_cookie(
            _OAUTH_STATE_COOKIE, path="/", secure=_sec, samesite=_ss, httponly=True
        )
        logger.info("oauth callback ok (google linked to account %s)", current_account_id)
        return resp

    # --- Normal sign-in: check for same-email auto-linking ---
    google_email = prof.get("email")
    existing_email_account = (
        db.query(Account)
        .filter(Account.email == google_email, Account.auth_provider == "email")
        .first()
        if google_email
        else None
    )

    if existing_email_account:
        # Auto-link: store Google creds under the existing email account, sign in as them
        target_id = existing_email_account.id
        try:
            google_token_store.save_credentials_json_for_account(target_id, raw_json)
        except Exception as exc:
            logger.exception("oauth auto-link save_credentials failed")
            raise HTTPException(500, "Could not store Google credentials.") from exc

        if prof.get("picture"):
            existing_email_account.picture = prof["picture"]
        existing_email_account.updated_at = datetime.utcnow()
        db.commit()
    else:
        # Standard Google sign-in: upsert account with Google sub as ID
        target_id = sub
        try:
            _upsert_account(db, sub, google_email, prof.get("name"), prof.get("picture"))
        except Exception as exc:
            logger.exception("oauth _upsert_account failed")
            if dbg:
                payload: dict = {
                    "step": "db_upsert_account",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
                payload.update(postgres_connection_diagnostics())
                return JSONResponse(status_code=500, content=payload)
            raise HTTPException(500, "Could not save account.") from exc

        try:
            google_token_store.save_credentials_json_for_account(sub, raw_json)
        except Exception as exc:
            logger.exception("oauth save_credentials_json_for_account failed")
            if dbg:
                return JSONResponse(
                    status_code=500,
                    content={
                        "step": "save_google_token",
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
            raise HTTPException(500, "Could not store Google credentials.") from exc

    resp = RedirectResponse(
        url=f"{POST_GOOGLE_OAUTH_FRONTEND_ORIGIN}/?google_connected=1"
    )
    try:
        session_tok = create_session_token(target_id)
    except RuntimeError as exc:
        logger.error("create_session_token: %s", exc)
        if dbg:
            return JSONResponse(
                status_code=503,
                content={
                    "step": "session_jwt",
                    "message": str(exc),
                    "has_SESSION_SECRET": bool(SESSION_SECRET),
                    "is_postgres": True,
                },
            )
        raise HTTPException(
            503,
            "SESSION_SECRET is required when using Postgres. Set it in .env / Railway and retry.",
        ) from exc
    resp.set_cookie(
        SESSION_COOKIE_NAME,
        session_tok,
        httponly=True,
        secure=_sec,
        samesite=_ss,
        max_age=SESSION_TTL_DAYS * 86400,
        path="/",
    )
    resp.delete_cookie(
        _OAUTH_STATE_COOKIE, path="/", secure=_sec, samesite=_ss, httponly=True
    )
    logger.info("oauth callback ok (postgres, account=%s)", target_id)
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


@router.get("/google/diagnostics")
def google_oauth_diagnostics():
    """Non-secret OAuth snapshot for local debugging (GET in browser)."""
    base = {
        "GOOGLE_REDIRECT_URI": GOOGLE_REDIRECT_URI,
        "FRONTEND_ORIGIN": FRONTEND_ORIGIN,
        "POST_GOOGLE_OAUTH_FRONTEND_ORIGIN": POST_GOOGLE_OAUTH_FRONTEND_ORIGIN,
        "is_postgres": is_postgres(),
        "has_SESSION_SECRET": bool(SESSION_SECRET),
        "credentials_file": str(CREDENTIALS_PATH),
        "credentials_file_exists": CREDENTIALS_PATH.is_file(),
        "web_oauth_env_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "debug_json_errors": _auth_debug_enabled(),
        "hint": "Set RECO_AUTH_DEBUG=1 (or RECO_DEBUG=1) for detailed JSON on OAuth callback errors. "
        "Watch backend logs on the reco.auth logger.",
    }
    base.update(postgres_connection_diagnostics())
    return base


@router.get("/google/status")
def google_status(request: Request):
    return _google_status_body(request)


@router.post("/google/disconnect")
def google_disconnect(
    request: Request,
    _account_id: str = Depends(require_account),
    db: Session = Depends(get_db),
):
    google_token_store.clear_credentials()
    # For Google-only accounts (no password), disconnecting Google means full sign-out.
    # For email accounts that linked Google, keep the session alive.
    account = db.get(Account, _account_id)
    sign_out = not account or getattr(account, "auth_provider", "google") == "google"
    resp = Response(status_code=204)
    if sign_out:
        _sec, _ss = _cookie_transport(request)
        resp.delete_cookie(
            SESSION_COOKIE_NAME, path="/", secure=_sec, samesite=_ss, httponly=True
        )
    return resp
