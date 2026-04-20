from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

REMI_HOME = Path(os.environ.get("REMI_HOME", str(Path.home() / ".remi")))
DB_PATH = REMI_HOME / "remi.db"
PROJECTS_DIR = REMI_HOME / "projects"
CREDENTIALS_PATH = REMI_HOME / "credentials.json"
TOKEN_PATH = REMI_HOME / "google_token.json"
LOGS_DIR = Path(os.environ.get("LOG_DIR", str(REMI_HOME / "logs")))

# Prefer DATABASE_URL (e.g. Supabase Postgres). Falls back to local SQLite.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip() or None
if DATABASE_URL:
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"


def is_postgres() -> bool:
    return bool(
        DATABASE_URL
        and DATABASE_URL.split(":", 1)[0].startswith("postgres")
    )


SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip() or None
# New-format key (sb_secret_...) is preferred; fall back to legacy service_role JWT
# so in-flight rotations don't break the backend. Publishable key is frontend-safe
# and not currently used server-side — surfaced for future client-side features.
SUPABASE_SECRET_KEY = (
    os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or None
)
# Back-compat alias: existing imports of SUPABASE_SERVICE_ROLE_KEY keep working.
SUPABASE_SERVICE_ROLE_KEY = SUPABASE_SECRET_KEY
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip() or None
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "project-docs").strip()


def use_supabase_storage() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SECRET_KEY)


def _normalize_browser_origin(value: str) -> str:
    """Match browser `Origin` headers: trim, strip wrapping quotes, no trailing slash."""
    o = value.strip()
    if len(o) >= 2 and o[0] == o[-1] and o[0] in "\"'":
        o = o[1:-1].strip()
    return o.rstrip("/")


# Model — NOT claude-opus-4-7, intentionally sonnet for cost/speed balance
ANTHROPIC_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
MAX_UPLOAD_SIZE_MB = 20
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Context token budgets — claude-sonnet-4-6 has 200K context window, use it
BUDGET_TRANSACTION = 1_000
BUDGET_PROFILE = 2_000
BUDGET_DOCUMENTS = 80_000   # ~60 pages of PA packages, inspection reports, etc.
BUDGET_EMAILS = 20_000
BUDGET_HISTORY_MESSAGES = 20
SUMMARY_TRIGGER_COUNT = 40

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# OAuth callback must match GCP "Authorized redirect URIs"
GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/api/auth/google/callback",
).strip()

# Where the browser lands after successful Google connect
FRONTEND_ORIGIN = _normalize_browser_origin(
    os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
)

# Web OAuth (production) — if set, used instead of ~/.remi/credentials.json
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip() or None
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip() or None

# CORS — comma-separated origins (include Vercel preview URLs if needed)
_cors_raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173").strip()
_seen_cors: set[str] = set()
CORS_ORIGINS: list[str] = []
for _part in _cors_raw.split(","):
    _o = _normalize_browser_origin(_part)
    if _o and _o not in _seen_cors:
        _seen_cors.add(_o)
        CORS_ORIGINS.append(_o)
# If FRONTEND_ORIGIN is set in env (non-default), also allow it for CORS — avoids
# duplicating the Vercel URL in both variables. Default localhost is already in CORS.
_env_frontend = os.environ.get("FRONTEND_ORIGIN", "").strip()
if _env_frontend:
    _fe = _normalize_browser_origin(_env_frontend)
    if _fe and _fe not in _seen_cors:
        _seen_cors.add(_fe)
        CORS_ORIGINS.append(_fe)

# Always allow resolved FRONTEND_ORIGIN (default http://localhost:5173) so split
# Vite + API works and empty CORS_ORIGINS cannot lock everyone out.
if FRONTEND_ORIGIN and FRONTEND_ORIGIN not in _seen_cors:
    _seen_cors.add(FRONTEND_ORIGIN)
    CORS_ORIGINS.append(FRONTEND_ORIGIN)

# Optional extra allowed Origin values (Starlette regex). Use for many Vercel preview URLs
# without listing each one, e.g. r"https://remi-ai[-\w]*\.vercel\.app"
# Validate at import: an invalid regex would otherwise crash *every* request when
# Starlette lazily compiles it inside CORSMiddleware.__init__ on first use.
import re as _re

_cors_regex = os.environ.get("CORS_ORIGIN_REGEX", "").strip()
CORS_ORIGIN_REGEX: str | None = None
if _cors_regex:
    try:
        _re.compile(_cors_regex)
        CORS_ORIGIN_REGEX = _cors_regex
    except _re.error as _exc:
        import logging as _logging

        _logging.getLogger("remi").error(
            "CORS_ORIGIN_REGEX %r is not a valid Python regex (%s). Ignoring it. "
            "Use a regex like r'https://your-app[-\\w]*\\.vercel\\.app' (NOT a glob like *.vercel.app).",
            _cors_regex,
            _exc,
        )

# Ensure runtime dirs exist (local / SQLite mode)
if not is_postgres():
    for _dir in (REMI_HOME, PROJECTS_DIR, LOGS_DIR):
        _dir.mkdir(parents=True, exist_ok=True)
else:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Multi-tenant session (Postgres + Google). SQLite uses implicit LOCAL_ACCOUNT_ID only.
LOCAL_ACCOUNT_ID = "local"
SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "remi_session").strip() or "remi_session"
SESSION_SECRET = os.environ.get("SESSION_SECRET", "").strip() or None
SESSION_TTL_DAYS = int(os.environ.get("SESSION_TTL_DAYS", "14") or "14")
