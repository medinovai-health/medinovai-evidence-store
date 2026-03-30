"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from src.db.connection import mos_async_session_maker
from src.settings import MosSettings, mos_get_settings


async def mos_get_settings_dep() -> MosSettings:
    """Inject settings."""
    return mos_get_settings()


async def mos_tenant_header(
    mos_x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    mos_settings: MosSettings = Depends(mos_get_settings_dep),
) -> str:
    """Resolve tenant from header or default."""
    if mos_settings.require_tenant_header and not mos_x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-Id required")
    return mos_x_tenant_id or mos_settings.tenant_id


async def mos_get_db_session() -> AsyncIterator[AsyncSession]:
    """Request-scoped async session with commit on success."""
    if mos_async_session_maker is None:
        raise HTTPException(status_code=503, detail="database unavailable")
    async with mos_async_session_maker() as mos_session:
        try:
            yield mos_session
            await mos_session.commit()
        except Exception:
            await mos_session.rollback()
            raise


def mos_get_temporal_client(request: Request) -> Client | None:
    """Return process-wide Temporal client from app lifespan."""
    return getattr(request.app.state, "mos_temporal_client", None)
