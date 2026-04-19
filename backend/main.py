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

    If a migration hangs or errors, /api/health stays available with the
    error so we can see what's wrong on Railway.
    """
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine

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

    # Optional: separate connection for migrations only. Use this if the runtime
    # pooler hangs on advisory locks or DDL (set MIGRATION_DATABASE_URL to the
    # direct, non-pooler Supabase URL on Railway).
    migration_url = os.environ.get("MIGRATION_DATABASE_URL", "").strip() or None
    if migration_url:
        logger.info("Using MIGRATION_DATABASE_URL for alembic upgrade (separate from runtime URL)")

    _alembic_ini = Path(__file__).parent / "alembic.ini"
    cfg = Config(str(_alembic_ini))
    if migration_url:
        cfg.set_main_option("sqlalchemy.url", migration_url.replace("%", "%%"))

    # Bound the migration so a stuck advisory lock or query is visible
    # within ~60s instead of silently hanging forever.
    mig_engine = create_engine(
        migration_url or os.environ["DATABASE_URL"],
        connect_args={"connect_timeout": 15},
        pool_pre_ping=True,
    )
    try:
        with mig_engine.connect() as c:
            c.execute(text("SET lock_timeout = '30s'"))
            c.execute(text("SET statement_timeout = '60s'"))
            c.execute(text("SET idle_in_transaction_session_timeout = '60s'"))
        logger.info("Alembic: starting upgrade head")
        command.upgrade(cfg, "head")
        logger.info("Alembic: upgrade head completed in %.0fms", (time.monotonic() - started) * 1000)
        DB_INIT_STATUS.update(
            ok=True,
            ran_at=time.time(),
            duration_ms=int((time.monotonic() - started) * 1000),
            error=None,
        )
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Alembic upgrade FAILED: %s\n%s", exc, tb)
        DB_INIT_STATUS.update(
            ok=False,
            ran_at=time.time(),
            duration_ms=int((time.monotonic() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        mig_engine.dispose()


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


@app.get("/api/debug/db")
def debug_db():
    """Counts and ownership snapshot of the live DB. Requires REMIP_DEBUG=1.

    Use this to verify which Supabase project the backend is talking to and
    whether your data is there but owned by a different account_id.
    """
    if os.environ.get("REMIP_DEBUG", "").strip().lower() not in ("1", "true", "yes"):
        return {"error": "REMIP_DEBUG not enabled"}

    out: dict = {"db": "postgres" if is_postgres() else "sqlite"}
    try:
        with engine.connect() as c:
            if is_postgres():
                out["server_version"] = c.execute(text("SHOW server_version")).scalar()
                out["current_database"] = c.execute(text("SELECT current_database()")).scalar()
                out["current_user"] = c.execute(text("SELECT current_user")).scalar()
                row = c.execute(text("SELECT inet_server_addr()::text, inet_server_port()")).fetchone()
                if row:
                    out["server_addr"] = row[0]
                    out["server_port"] = row[1]
                ver = c.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                out["alembic_version"] = ver[0] if ver else None

            tables = ["accounts", "projects", "google_oauth_credentials", "documents", "email_threads", "email_messages"]
            counts: dict = {}
            for t in tables:
                try:
                    counts[t] = c.execute(text(f"SELECT count(*) FROM {t}")).scalar()
                except Exception as exc:
                    counts[t] = f"error: {type(exc).__name__}: {exc}"
            out["counts"] = counts

            try:
                rows = c.execute(
                    text(
                        "SELECT owner_id, count(*) AS n FROM projects GROUP BY owner_id ORDER BY n DESC"
                    )
                ).fetchall()
                out["projects_by_owner"] = [{"owner_id": r[0], "count": r[1]} for r in rows]
            except Exception as exc:
                out["projects_by_owner_error"] = f"{type(exc).__name__}: {exc}"

            try:
                rows = c.execute(
                    text("SELECT id, email, name FROM accounts ORDER BY created_at NULLS LAST")
                ).fetchall()
                out["accounts"] = [{"id": r[0], "email": r[1], "name": r[2]} for r in rows]
            except Exception as exc:
                out["accounts_error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


# Serve built frontend in production (single-origin deploy)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
