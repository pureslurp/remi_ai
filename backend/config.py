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
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip() or None
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "project-docs").strip()


def use_supabase_storage() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


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
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")

# Web OAuth (production) — if set, used instead of ~/.remi/credentials.json
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip() or None
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip() or None

# CORS — comma-separated origins (include Vercel preview URLs if needed)
_cors = os.environ.get("CORS_ORIGINS", "http://localhost:5173").strip()
CORS_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()]

# Ensure runtime dirs exist (local / SQLite mode)
if not is_postgres():
    for _dir in (REMI_HOME, PROJECTS_DIR, LOGS_DIR):
        _dir.mkdir(parents=True, exist_ok=True)
else:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
