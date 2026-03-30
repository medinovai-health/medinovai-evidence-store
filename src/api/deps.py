"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

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
