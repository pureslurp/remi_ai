import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logging.config import fileConfig

from alembic import context

from config import SQLALCHEMY_DATABASE_URI
from database import Base, engine
import models  # noqa: F401 — register all ORM models

config = context.config
escaped = SQLALCHEMY_DATABASE_URI.replace("%", "%%")
config.set_main_option("sqlalchemy.url", escaped)

if config.config_file_name is not None:
    # disable_existing_loggers=False is critical: the default True wipes the
    # 'remi' / 'uvicorn.error' loggers, hiding every log line after migrations
    # run (including the uvicorn 'Started server process' banner).
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
