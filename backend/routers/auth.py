import json
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from config import (
    CREDENTIALS_PATH,
    FRONTEND_ORIGIN,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_SCOPES,
)
from services import google_token_store

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _google_user_profile(access_token: str) -> dict:
    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
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


@router.get("/google/url")
def google_auth_url():
    try:
        flow = _get_flow()
    except FileNotFoundError:
        raise HTTPException(
            400,
            "credentials.json not found at ~/.remi/credentials.json. "
            "See README for GCP setup, or set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET for web OAuth.",
        )
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return {"url": auth_url}


@router.get("/google/callback")
def google_callback(code: str):
    flow = _get_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    google_token_store.save_credentials_json(creds.to_json())
    return RedirectResponse(url=f"{FRONTEND_ORIGIN}/?google_connected=1")


@router.get("/google/status")
def google_status():
    if not google_token_store.credentials_exist():
        return {"authenticated": False, "reason": "not_connected"}
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        info = google_token_store.credentials_to_info()
        if not info:
            return {"authenticated": False, "reason": "not_connected"}
        creds = Credentials.from_authorized_user_info(info, GOOGLE_SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
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


@router.post("/google/disconnect", status_code=204)
def google_disconnect():
    google_token_store.clear_credentials()
