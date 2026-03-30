"""Audit trail read API."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import mos_get_db_session
from src.db.repository import AuditRepo

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/studies/{study_id}")
async def mos_audit_for_study(
    study_id: str,
    mos_session: Annotated[AsyncSession, Depends(mos_get_db_session)],
) -> dict[str, Any]:
    """Return audit events for a study from PostgreSQL."""
    try:
        mos_uid = uuid.UUID(study_id)
    except ValueError as mos_exc:
        raise HTTPException(status_code=400, detail="invalid study id") from mos_exc
    mos_events = await AuditRepo(mos_session).mos_list_for_study(mos_uid)
    return {
        "study_id": study_id,
        "count": len(mos_events),
        "events": [
            {
                "event_id": str(e.id),
                "timestamp_utc": e.event_at.isoformat(),
                "actor_id": e.actor_id,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "reason": e.reason,
                "correlation_id": (
                    (e.new_value_json or {}).get("correlation_id")
                    if isinstance(e.new_value_json, dict)
                    else None
                ),
            }
            for e in mos_events
        ],
        "phi_safe": True,
    }
