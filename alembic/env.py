"""Alembic env.py for DeepBl4nder — reads DB URL from DeepBl4nder_DB env var."""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add project root to sys.path so we can import DeepBl4nder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from DeepBl4nder.api.db import Base
# Import all models so Alembic can detect them for autogenerate
from DeepBl4nder.api import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Resolve database URL from environment or fallback to default
_db_url = os.environ.get("DeepBl4nder_DB", "DeepBl4nder.db")
if "://" not in _db_url:
    from pathlib import Path
    _db_url = f"sqlite:///{Path(_db_url).expanduser().resolve().as_posix()}"
config.set_main_option("sqlalchemy.url", _db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (apply to live database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
