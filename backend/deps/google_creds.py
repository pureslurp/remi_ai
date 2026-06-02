"""Shared Google OAuth credentials for Gmail, Drive, and Picker."""

from __future__ import annotations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from config import GOOGLE_SCOPES
from services import google_token_store


def get_google_credentials() -> Credentials:
    """Return refreshed Google credentials for the current request account."""
    if not google_token_store.credentials_exist():
        raise RuntimeError("Google not authenticated. Connect Google in settings.")

    info = google_token_store.credentials_to_info()
    if not info:
        raise RuntimeError("Google not authenticated. Connect Google in settings.")

    creds = Credentials.from_authorized_user_info(info, GOOGLE_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        google_token_store.save_credentials_json(creds.to_json())
    if not creds.valid or not creds.token:
        raise RuntimeError("Google token expired. Reconnect Google in settings.")
    return creds
