"""Health and readiness endpoints."""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text

from src.api.deps import mos_get_settings_dep
from src.db.connection import mos_async_session_maker
from src.settings import MosSettings

router = APIRouter(tags=["health"])


@router.get("/health")
async def mos_health() -> dict[str, Any]:
    """Liveness probe."""
    return {
        "status": "healthy",
        "service": os.getenv("MOS_SERVICE_NAME", "medinovai-evidence-store"),
        "phi_safe": True,
    }


@router.get("/ready")
async def mos_ready(
    mos_settings: Annotated[MosSettings, Depends(mos_get_settings_dep)],
) -> dict[str, Any]:
    """Readiness — verifies database pool when persistence is enabled."""
    if mos_settings.skip_db or mos_async_session_maker is None:
        return {"status": "ready", "phi_safe": True, "db": "skipped"}
    async with mos_async_session_maker() as mos_session:
        await mos_session.execute(text("SELECT 1"))
    return {"status": "ready", "phi_safe": True, "db": "ok"}
