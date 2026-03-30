"""Health and readiness endpoints."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

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
async def mos_ready() -> dict[str, Any]:
    """Readiness — extend with Temporal ping when wired."""
    return {"status": "ready", "phi_safe": True}
