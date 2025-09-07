from __future__ import with_statement

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
import sys

sys.path.append(os.getcwd())

from app.extensions import db
from flask import current_app
from app.models import *  # noqa: F401,F403, import models metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
# Ensure SQLAlchemy URL comes from Flask app config (not alembic.ini)
try:
    config.set_main_option("sqlalchemy.url", current_app.config.get("SQLALCHEMY_DATABASE_URI", ""))
except Exception:
    pass

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        # If logging config file is missing, proceed without configuring logging
        pass

target_metadata = db.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),  # type: ignore[arg-type]
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


