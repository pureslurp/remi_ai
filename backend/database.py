from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import SQLALCHEMY_DATABASE_URI, is_postgres

_connect_args = {}
_engine_kwargs = {"pool_pre_ping": True}

if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    _engine_kwargs = {}
elif SQLALCHEMY_DATABASE_URI.split(":", 1)[0].startswith("postgres"):
    # Avoid hanging forever on bad host/firewall (Railway → 502 "application not responding")
    _connect_args = {"connect_timeout": 15}

engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    connect_args=_connect_args,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
