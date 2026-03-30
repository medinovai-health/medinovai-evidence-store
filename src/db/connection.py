"""Async engine and session factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.db.models import MosBase

if TYPE_CHECKING:
    pass

E_DEFAULT_POOL_SIZE = 5
E_MAX_OVERFLOW = 10

mos_engine: AsyncEngine | None = None
mos_async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def mos_init_db(mos_database_url: str) -> None:
    """Create async engine and session maker."""
    global mos_engine, mos_async_session_maker
    mos_engine = create_async_engine(
        mos_database_url,
        pool_pre_ping=True,
        pool_size=E_DEFAULT_POOL_SIZE,
        max_overflow=E_MAX_OVERFLOW,
    )
    mos_async_session_maker = async_sessionmaker(
        mos_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def mos_close_db() -> None:
    """Dispose engine."""
    global mos_engine, mos_async_session_maker
    if mos_engine is not None:
        await mos_engine.dispose()
    mos_engine = None
    mos_async_session_maker = None


async def mos_create_schema() -> None:
    """Create tables if missing (dev); production should use Alembic."""
    if mos_engine is None:
        raise RuntimeError("Database not initialized; call mos_init_db first")
    async with mos_engine.begin() as mos_conn:
        await mos_conn.run_sync(MosBase.metadata.create_all)
