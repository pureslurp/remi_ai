from pathlib import Path
import logging
import os
import shutil

from dotenv import load_dotenv

# override=True: values in .env win over pre-set shell env (e.g. stale DATABASE_URL).
# Default dotenv behavior leaves existing env vars untouched, which breaks local dev
# when the shell still has an old direct Supabase host but .env was updated to pooler.
load_dotenv(Path(__file__).parent.parent / ".env", override=True)
# Optional backend-local overrides (fills vars not already set from repo root .env).
load_dotenv(Path(__file__).parent / ".env", override=False)

# Primary env var is RECO_HOME; fall back to legacy KOVA_HOME and REMI_HOME so existing
# deployments with old vars keep booting during rename.
_reco_home_env = os.environ.get("RECO_HOME", "").strip()
_legacy_kova_home_env = os.environ.get("KOVA_HOME", "").strip()
_legacy_remi_home_env = os.environ.get("REMI_HOME", "").strip()
RECO_HOME = Path(
    _reco_home_env or _legacy_kova_home_env or _legacy_remi_home_env or str(Path.home() / ".reco")
)

# One-time, best-effort migration of legacy data dirs to ~/.reco for local dev users
# upgrading in place. Never crash startup on a cosmetic rename — the DB is
# authoritative and failures here just mean the old dir is still around.
_legacy_kova_home = Path.home() / ".kova"
_legacy_remi_home = Path.home() / ".remi"
try:
    if not _reco_home_env and not _legacy_kova_home_env and not _legacy_remi_home_env:
        if _legacy_kova_home.exists() and not RECO_HOME.exists():
            shutil.move(str(_legacy_kova_home), str(RECO_HOME))
            logging.getLogger("reco").info(
                "Migrated legacy data dir %s -> %s", _legacy_kova_home, RECO_HOME
            )
        elif _legacy_remi_home.exists() and not RECO_HOME.exists():
            shutil.move(str(_legacy_remi_home), str(RECO_HOME))
            logging.getLogger("reco").info(
                "Migrated legacy data dir %s -> %s", _legacy_remi_home, RECO_HOME
            )
except Exception as _exc:  # noqa: BLE001 — best-effort migration
    logging.getLogger("reco").warning("Legacy data dir migration skipped: %s", _exc)

DB_PATH = RECO_HOME / "reco.db"
# If migrated from a legacy install, rename old db to reco.db once.
try:
    for _legacy_db_name in ("kova.db", "remi.db"):
        _legacy_db = RECO_HOME / _legacy_db_name
        if _legacy_db.exists() and not DB_PATH.exists():
            _legacy_db.rename(DB_PATH)
            logging.getLogger("reco").info("Renamed %s -> %s", _legacy_db, DB_PATH)
            break
except Exception as _exc:  # noqa: BLE001
    logging.getLogger("reco").warning("Legacy db rename skipped: %s", _exc)

PROJECTS_DIR = RECO_HOME / "projects"
CREDENTIALS_PATH = RECO_HOME / "credentials.json"
TOKEN_PATH = RECO_HOME / "google_token.json"
LOGS_DIR = Path(os.environ.get("LOG_DIR", str(RECO_HOME / "logs")))

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


def postgres_connection_diagnostics() -> dict[str, str | bool | None]:
    """Safe fields for /api/auth/google/diagnostics — no passwords."""
    out: dict[str, str | bool | None] = {
        "database_url_configured": bool(DATABASE_URL),
        "postgres_mode": bool(is_postgres()),
        "database_url_hostname": None,
        "looks_like_supabase_direct_db_host": False,
        "local_dev_hint": None,
    }
    if not DATABASE_URL or not is_postgres():
        return out
    hostname: str | None = None
    try:
        from urllib.parse import urlparse

        raw = DATABASE_URL.strip()
        if "://" in raw and raw.split("://", 1)[0].startswith("postgresql+"):
            raw = "postgresql://" + raw.split("://", 1)[1]
        u = urlparse(raw)
        hostname = u.hostname
    except Exception:
        hostname = None
    out["database_url_hostname"] = hostname
    direct = bool(
        hostname
        and hostname.startswith("db.")
        and "supabase.co" in hostname
        and "pooler" not in hostname
    )
    out["looks_like_supabase_direct_db_host"] = direct
    if direct:
        out["local_dev_hint"] = (
            "Replace DATABASE_URL with the Session pooler URI from Supabase → Connect "
            "(Session mode / IPv4). Do not use the 'Direct connection' host db.*.supabase.co "
            "on a Mac/home network — it often resolves to IPv6 and fails with connection refused."
        )
    return out


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
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip()
# OpenAI / Gemini defaults when project has no llm_model set (override via env)
OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip()
GEMINI_CHAT_MODEL = os.environ.get("GEMINI_CHAT_MODEL", "gemini-2.0-flash").strip()
# anthropic | openai | gemini — used when project.llm_provider is null
DEFAULT_LLM_PROVIDER = os.environ.get("DEFAULT_LLM_PROVIDER", "anthropic").strip().lower()
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4096") or "4096")

# --- Trial & Pro usage (managed keys; see usage_entitlements.py + chat_token_estimate.py) ---
#
# Quotas are **billable units**, not raw provider tokens:
#   billable = input_tokens + (output_tokens * OUTPUT_TOKEN_QUOTA_MULTIPLIER)
# Output is weighted because list pricing is usually much higher $/token for output than input.
# Set multiplier ≈ (your output $/MTok) / (your input $/MTok) for your primary Pro model, e.g. ~3–5.
#
# Rough COGS sanity (planning only — verify current vendor list prices):
#   implied_monthly_cogs_usd ≈ (PRO_INCLUDED_TOKENS_PER_MONTH / 1e6) * blended_usd_per_million_billable
# Example: 3M billable units at ~$8/M blended → ~$24 COGS/month before overage.
#
TRIAL_MAX_DAYS = int(os.environ.get("TRIAL_MAX_DAYS", "14") or "14")
# Free / trial tier: lifetime token cap (not monthly — no billing relationship)
TRIAL_MAX_TOKENS = int(os.environ.get("TRIAL_MAX_TOKENS", "500000") or "500000")
FREE_MAX_TOKENS = TRIAL_MAX_TOKENS  # alias; "trial" and "free" share the same cap
# Paid tier monthly allowances (billable units = input + output × OUTPUT_TOKEN_QUOTA_MULTIPLIER)
PRO_INCLUDED_TOKENS_PER_MONTH = int(
    os.environ.get("PRO_INCLUDED_TOKENS_PER_MONTH", "2000000") or "2000000"
)
MAX_INCLUDED_TOKENS_PER_MONTH = int(
    os.environ.get("MAX_INCLUDED_TOKENS_PER_MONTH", "6000000") or "6000000"
)
ULTRA_INCLUDED_TOKENS_PER_MONTH = int(
    os.environ.get("ULTRA_INCLUDED_TOKENS_PER_MONTH", "10000000") or "10000000"
)
# Each output token counts this many times toward caps (input tokens count as 1×).
OUTPUT_TOKEN_QUOTA_MULTIPLIER = float(os.environ.get("OUTPUT_TOKEN_QUOTA_MULTIPLIER", "3.0") or "3.0")
# Comma-separated emails that bypass all token quotas (admin accounts).
ADMIN_EMAILS: frozenset[str] = frozenset(
    e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()
)
# Optional: shown in 402 responses and GET /api/account/entitlements (Stripe checkout or marketing URL)
UPGRADE_CHECKOUT_URL = os.environ.get("UPGRADE_CHECKOUT_URL", "").strip() or None

# --- Stripe ---
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip() or None
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip() or None
# Stripe Price IDs for each paid plan (create in Stripe dashboard → Products)
STRIPE_PRICE_PRO = os.environ.get("STRIPE_PRICE_PRO", "").strip() or None
STRIPE_PRICE_MAX = os.environ.get("STRIPE_PRICE_MAX", "").strip() or None
STRIPE_PRICE_ULTRA = os.environ.get("STRIPE_PRICE_ULTRA", "").strip() or None
# RealEstateAPI (Option B public property data — server key only; see docs/real-estateapi-v1.md)
REALESTATEAPI_BACKEND = (
    os.environ.get("REALESTATEAPI_BACKEND", "").strip()
    or os.environ.get("REAL_ESTATE_API_KEY", "").strip()
    or None
)
# When unset, defaults to "on" iff a server key is present. Set REALESTATEAPI_ENABLED=0 to turn off
# all vendor property-data calls and product UI, even if the key remains in the environment.
_reapi_en_raw = os.environ.get("REALESTATEAPI_ENABLED", "").strip().lower()
if _reapi_en_raw == "":
    REALESTATEAPI_ENABLED = bool(REALESTATEAPI_BACKEND)
else:
    REALESTATEAPI_ENABLED = _reapi_en_raw in ("1", "true", "yes", "on")
REAPI_ACTIVE = bool(REALESTATEAPI_BACKEND) and REALESTATEAPI_ENABLED
# Client-side key (if any) is not read by the backend client — reserved for future browser-only flows
REALESTATEAPI_FRONTEND = (
    os.environ.get("REALESTATEAPI_FRONTEND", "").strip()
    or os.environ.get("REAL_ESTATE_API_FRONTEND", "").strip()
    or None
)
REALESTATEAPI_BASE_URL = os.environ.get(
    "REALESTATEAPI_BASE_URL", "https://api.realestateapi.com"
).rstrip("/")
# TTL seconds for in-memory address cache (reduces repeat PropertyDetail calls in chat)
REALESTATEAPI_CACHE_TTL_SECONDS = int(
    os.environ.get("REALESTATEAPI_CACHE_TTL_SECONDS", "300") or "300"
)

MAX_UPLOAD_SIZE_MB = 20
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Context token budgets — claude-sonnet-4-6 has 200K context window, use it
BUDGET_TRANSACTION = 1_000
BUDGET_PROFILE = 2_000
BUDGET_DOCUMENTS = 80_000   # ~60 pages of PA packages, inspection reports, etc.
BUDGET_EMAILS = 20_000
# Live chat turns sent to the main model; older content is in conversation summary
BUDGET_HISTORY_MESSAGES = 10
SUMMARY_TRIGGER_COUNT = 40
# Pre-filter: include threads with activity in the last N days (union with active-tx tags)
EMAIL_TRIAGE_DAYS = int(os.environ.get("EMAIL_TRIAGE_DAYS", "45") or "45")
# Cap candidate email threads before LLM triage
TRIAGE_MAX_EMAIL_THREADS = 50

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    # gmail.compose — not requested in GCP for now; see gmail_service.create_gmail_draft
    # "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# OAuth callback must match GCP "Authorized redirect URIs".
# Default port 5173 matches Vite dev (`/api` proxied); cookie + redirect stay on the same origin.
GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:5173/api/auth/google/callback",
).strip()

# Where the browser lands after successful Google connect
FRONTEND_ORIGIN = _normalize_browser_origin(
    os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
)


def _origin_from_absolute_url(url: str) -> str | None:
    from urllib.parse import urlparse

    u = urlparse(url.strip())
    if not u.scheme or not u.netloc:
        return None
    return _normalize_browser_origin(f"{u.scheme}://{u.netloc}")


def _hostname_is_local_dev(hostname: str | None) -> bool:
    if not hostname:
        return False
    return hostname.lower() in ("localhost", "127.0.0.1", "[::1]")


def _post_google_oauth_browser_redirect_origin() -> str:
    """Browser URL after Google OAuth completes.

    The session cookie is always tied to the host that served ``GOOGLE_REDIRECT_URI``
    (e.g. Vite on localhost:5173 with ``/api`` proxied). If ``FRONTEND_ORIGIN`` in
    ``.env`` is set to production (Vercel) for deploy docs, redirecting there after
    local OAuth drops the localhost cookie and looks like a failed login.

    When the redirect URI is clearly local dev, send the user back to that origin.
    Otherwise keep ``FRONTEND_ORIGIN`` so API-on-a-subdomain + SPA-on-Vercel still works.
    """
    ru_origin = _origin_from_absolute_url(GOOGLE_REDIRECT_URI)
    if not ru_origin:
        return FRONTEND_ORIGIN
    if ru_origin == FRONTEND_ORIGIN:
        return FRONTEND_ORIGIN
    from urllib.parse import urlparse

    host = urlparse(GOOGLE_REDIRECT_URI.strip()).hostname
    if _hostname_is_local_dev(host):
        return ru_origin
    return FRONTEND_ORIGIN


POST_GOOGLE_OAUTH_FRONTEND_ORIGIN = _post_google_oauth_browser_redirect_origin()

# Web OAuth (production) — if set, used instead of ~/.reco/credentials.json
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
# without listing each one, e.g. r"https://reco[-\w]*\.vercel\.app"
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

        _logging.getLogger("reco").error(
            "CORS_ORIGIN_REGEX %r is not a valid Python regex (%s). Ignoring it. "
            "Use a regex like r'https://your-app[-\\w]*\\.vercel\\.app' (NOT a glob like *.vercel.app).",
            _cors_regex,
            _exc,
        )

# Ensure runtime dirs exist (local / SQLite mode)
if not is_postgres():
    for _dir in (RECO_HOME, PROJECTS_DIR, LOGS_DIR):
        _dir.mkdir(parents=True, exist_ok=True)
else:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Multi-tenant session (Postgres + Google). SQLite uses implicit LOCAL_ACCOUNT_ID only.
LOCAL_ACCOUNT_ID = "local"
SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "reco_session").strip() or "reco_session"
SESSION_SECRET = os.environ.get("SESSION_SECRET", "").strip() or None
SESSION_TTL_DAYS = int(os.environ.get("SESSION_TTL_DAYS", "14") or "14")
