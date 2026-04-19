import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from config import CORS_ORIGINS, GOOGLE_CLIENT_ID, LOGS_DIR, is_postgres
from sqlalchemy import text

# Configure logging to file + console (file optional if not writable)
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
)
logger = logging.getLogger("remi")

from database import engine, Base
import models  # ensure all ORM models are registered

if is_postgres():
    _dbu = urlparse(os.environ.get("DATABASE_URL", ""))
    logger.info(
        "Postgres target host=%s port=%s user=%s database=%s",
        _dbu.hostname,
        _dbu.port,
        _dbu.username,
        (_dbu.path or "/").lstrip("/") or "postgres",
    )
    if _dbu.hostname and "pooler.supabase.com" in _dbu.hostname:
        if _dbu.username == "postgres":
            logger.warning(
                "DATABASE_URL user is 'postgres' but host is the Supavisor pooler. "
                "Session pooler strings almost always need user postgres.<YOUR_PROJECT_REF> "
                "(copy the full URI from Supabase → Connect → Session pooler). "
                "Wrong user causes auth failure and 502 on boot."
            )
    from alembic.config import Config
    from alembic import command

    _alembic_ini = Path(__file__).parent / "alembic.ini"
    command.upgrade(Config(str(_alembic_ini)), "head")
else:
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

from routers import projects, properties, transactions, documents, chat, auth, gmail, drive

app = FastAPI(title="REMI AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS allow_origins=%s", CORS_ORIGINS)
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
    return {"status": "ok"}


# Serve built frontend in production (single-origin deploy)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
