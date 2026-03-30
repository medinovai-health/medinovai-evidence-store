"""Alembic async migration environment (asyncpg)."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.db.models import MosBase

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = MosBase.metadata


def mos_get_url() -> str:
    """Database URL from environment (asyncpg)."""
    return os.environ.get(
        "MOS_DATABASE_URL",
        "postgresql+asyncpg://evidence:evidence@127.0.0.1:5433/evidence",
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=mos_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(mos_connection: Connection) -> None:
    """Configure context from a live connection."""
    context.configure(connection=mos_connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create async engine and run migrations."""
    mos_configuration = config.get_section(config.config_ini_section) or {}
    mos_configuration["sqlalchemy.url"] = mos_get_url()
    mos_connectable = async_engine_from_config(
        mos_configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with mos_connectable.connect() as mos_connection:
        await mos_connection.run_sync(do_run_migrations)
    await mos_connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
