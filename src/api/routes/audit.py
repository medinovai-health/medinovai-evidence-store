"""Audit trail read API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.compliance.audit_trail import E_GLOBAL_AUDIT

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/studies/{study_id}")
async def mos_audit_for_study(study_id: str) -> dict[str, Any]:
    """Return audit events whose resource_id matches study (scaffold filter)."""
    mos_events = E_GLOBAL_AUDIT.mos_query_by_study(study_id)
    return {
        "study_id": study_id,
        "count": len(mos_events),
        "events": [
            {
                "event_id": e.event_id,
                "timestamp_utc": e.timestamp_utc,
                "actor_id": e.actor_id,
                "action": e.action,
                "category": e.category,
                "reason": e.reason,
                "correlation_id": e.correlation_id,
            }
            for e in mos_events
        ],
        "phi_safe": True,
    }
