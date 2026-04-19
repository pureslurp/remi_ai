import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from config import CORS_ORIGINS, LOGS_DIR, is_postgres
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
