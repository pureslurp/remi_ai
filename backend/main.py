import logging
import os
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

load_dotenv(Path(__file__).parent.parent / ".env")

from config import CORS_ORIGIN_REGEX, CORS_ORIGINS, GOOGLE_CLIENT_ID, LOGS_DIR, is_postgres, SESSION_SECRET
from sqlalchemy import text

# Configure logging to file + console (file optional if not writable).
# force=True so any prior basicConfig (e.g. from a transitive import) does not win.
_log_handlers = [logging.StreamHandler()]
try:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _log_handlers.append(logging.FileHandler(LOGS_DIR / "remi.log"))
except OSError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=_log_handlers,
    force=True,
)
logger = logging.getLogger("remi")

from database import engine, Base
import models  # ensure all ORM models are registered

# Tracks last DB bootstrap result; surfaced at /api/health so we can diagnose
# a sick container without crashing the whole process at import time.
DB_INIT_STATUS: dict = {"ok": False, "ran_at": None, "duration_ms": None, "error": None}


def _bootstrap_postgres() -> None:
    """Run Alembic upgrade head, but never let it kill the process.

    A migration failure is logged with full traceback and surfaced via
    /api/health (db_init_ok=false, db_init_error=...) instead of crashing
    uvicorn before it can serve a single request.
    """
    from alembic.config import Config
    from alembic import command

    started = time.monotonic()
    _dbu = urlparse(os.environ.get("DATABASE_URL", ""))
    logger.info(
        "Postgres target host=%s port=%s user=%s database=%s",
        _dbu.hostname,
        _dbu.port,
        _dbu.username,
        (_dbu.path or "/").lstrip("/") or "postgres",
    )
    if _dbu.hostname and "pooler.supabase.com" in _dbu.hostname and _dbu.username == "postgres":
        logger.warning(
            "DATABASE_URL user is 'postgres' but host is the Supavisor pooler. "
            "Session pooler strings need user postgres.<PROJECT_REF>. Wrong user -> auth failure / hang."
        )

    _alembic_ini = Path(__file__).parent / "alembic.ini"
    try:
        logger.info("Alembic: starting upgrade head")
        command.upgrade(Config(str(_alembic_ini)), "head")
        logger.info("Alembic: upgrade head completed in %.0fms", (time.monotonic() - started) * 1000)
        DB_INIT_STATUS.update(
            ok=True,
            ran_at=time.time(),
            duration_ms=int((time.monotonic() - started) * 1000),
            error=None,
        )
    except Exception as exc:
        logger.error("Alembic upgrade FAILED: %s\n%s", exc, traceback.format_exc())
        DB_INIT_STATUS.update(
            ok=False,
            ran_at=time.time(),
            duration_ms=int((time.monotonic() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )


def _bootstrap_sqlite() -> None:
    started = time.monotonic()
    try:
        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(projects)")).fetchall()}
            if cols and "gmail_address_rules" not in cols:
                conn.execute(text("ALTER TABLE projects ADD COLUMN gmail_address_rules TEXT DEFAULT '{}'"))
                conn.commit()
            dcols = {row[1] for row in conn.execute(text("PRAGMA table_info(documents)")).fetchall()}
            if dcols and "storage_object_key" not in dcols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN storage_object_key VARCHAR"))
                conn.commit()
            tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
            if "accounts" not in tables:
                conn.execute(
                    text(
                        "CREATE TABLE accounts (id VARCHAR NOT NULL PRIMARY KEY, email VARCHAR, "
                        "name VARCHAR, picture VARCHAR, created_at DATETIME, updated_at DATETIME)"
                    )
                )
                conn.commit()
            acols = {row[1] for row in conn.execute(text("PRAGMA table_info(projects)")).fetchall()}
            if acols and "owner_id" not in acols:
                conn.execute(text("ALTER TABLE projects ADD COLUMN owner_id VARCHAR"))
                conn.commit()
            conn.execute(
                text(
                    "INSERT OR IGNORE INTO accounts (id, email, name, picture, created_at, updated_at) "
                    "VALUES ('local', 'local@sqlite', NULL, NULL, datetime('now'), datetime('now'))"
                )
            )
            conn.commit()
            conn.execute(text("UPDATE projects SET owner_id = 'local' WHERE owner_id IS NULL"))
            conn.commit()
            try:
                conn.execute(
                    text("UPDATE google_oauth_credentials SET id = 'local' WHERE id = 'default'")
                )
                conn.commit()
            except Exception:
                conn.rollback()
        DB_INIT_STATUS.update(
            ok=True,
            ran_at=time.time(),
            duration_ms=int((time.monotonic() - started) * 1000),
            error=None,
        )
    except Exception as exc:
        logger.error("SQLite bootstrap FAILED: %s\n%s", exc, traceback.format_exc())
        DB_INIT_STATUS.update(
            ok=False,
            ran_at=time.time(),
            duration_ms=int((time.monotonic() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )


if is_postgres():
    _bootstrap_postgres()
else:
    _bootstrap_sqlite()

from routers import projects, properties, transactions, documents, chat, auth, gmail, drive


class ApiNoCacheMiddleware:
    """
    Railway's edge (Fastly) may cache GET /api/* responses. Probes without an Origin
    header get 401/200 without Access-Control-Allow-Origin; serving that cached object
    to a browser that sends Origin triggers a false CORS failure. Strong no-store +
    Vary: Origin reduces bad cache hits; Surrogate-Control helps Fastly skip cache.

    Implemented as pure ASGI (not BaseHTTPMiddleware) to avoid Starlette edge-case 500s.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start" and path.startswith("/api/"):
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "private, no-store, must-revalidate"
                headers["Pragma"] = "no-cache"
                headers["Expires"] = "0"
                headers["Surrogate-Control"] = "no-store"
                vary = headers.get("vary", "")
                parts = [p.strip() for p in vary.split(",") if p.strip()] if vary else []
                lows = {p.lower() for p in parts}
                if "origin" not in lows:
                    parts.append("Origin")
                    headers["vary"] = ", ".join(parts)
            await send(message)

        await self.app(scope, receive, send_wrapper)


app = FastAPI(title="REMI AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Runs outermost on the response path so headers apply after CORS.
app.add_middleware(ApiNoCacheMiddleware)
logger.info(
    "CORS allow_origins=%s allow_origin_regex=%s",
    CORS_ORIGINS,
    CORS_ORIGIN_REGEX or "(none)",
)
if is_postgres() and GOOGLE_CLIENT_ID and not SESSION_SECRET:
    logger.error(
        "SESSION_SECRET is REQUIRED when DATABASE_URL is Postgres and GOOGLE_CLIENT_ID is set. "
        "Auth endpoints will return 500. Set SESSION_SECRET on Railway (long random string) and redeploy."
    )

if is_postgres() and GOOGLE_CLIENT_ID and not os.environ.get("FRONTEND_ORIGIN", "").strip():
    logger.warning(
        "FRONTEND_ORIGIN is unset. After Google OAuth, redirects go to the default "
        "http://localhost:5173/?google_connected=1. Set FRONTEND_ORIGIN on Railway to your "
        "Vercel origin (same URL as in CORS), e.g. https://your-app.vercel.app"
    )

app.include_router(projects.router)
app.include_router(properties.router)
app.include_router(transactions.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(gmail.router)
app.include_router(drive.router)


@app.get("/api/health")
def health():
    """Always returns 200 so we can see container state even when DB is sick."""
    out: dict = {
        "status": "ok",
        "db_init_ok": bool(DB_INIT_STATUS.get("ok")),
    }
    if not DB_INIT_STATUS.get("ok") and DB_INIT_STATUS.get("error"):
        out["db_init_error"] = DB_INIT_STATUS["error"]
    if os.environ.get("REMIP_DEBUG", "").strip().lower() in ("1", "true", "yes"):
        out["cors_origins"] = list(CORS_ORIGINS)
        out["cors_origin_regex"] = CORS_ORIGIN_REGEX
        out["postgres"] = bool(is_postgres())
        out["has_google_client_id"] = bool(GOOGLE_CLIENT_ID)
        out["has_session_secret"] = bool(SESSION_SECRET)
        out["db_init"] = DB_INIT_STATUS
    return out


# Serve built frontend in production (single-origin deploy)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
