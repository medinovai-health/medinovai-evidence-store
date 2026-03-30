"""Append-only audit trail sink (in-memory scaffold; replace with WORM store)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

import structlog

mos_logger = structlog.get_logger()

E_AUDIT_CATEGORY_STUDY = "STUDY_LIFECYCLE"
E_AUDIT_CATEGORY_SIGNATURE = "SIGNATURE"
E_AUDIT_CATEGORY_ARTIFACT = "ARTIFACT_MUTATION"


@dataclass
class MosAuditEvent:
    """Single immutable audit event."""

    event_id: str
    timestamp_utc: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    reason: str
    correlation_id: str
    tenant_id: str
    category: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MosAuditTrailBuffer:
    """Process-local append-only buffer (scaffold)."""

    def __init__(self) -> None:
        self._mos_events: list[MosAuditEvent] = []
        self._mos_lock = Lock()

    def mos_append(
        self,
        *,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        reason: str,
        correlation_id: str,
        tenant_id: str,
        category: str,
        metadata: dict[str, Any] | None = None,
    ) -> MosAuditEvent:
        """Append one audit row."""
        mos_ev = MosAuditEvent(
            event_id=str(uuid4()),
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            reason=reason,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            category=category,
            metadata=metadata or {},
        )
        with self._mos_lock:
            self._mos_events.append(mos_ev)
        mos_logger.info(
            "audit_event",
            event_id=mos_ev.event_id,
            category=category,
            action=action,
            resource_id=resource_id,
            phi_safe=True,
        )
        return mos_ev

    def mos_query_by_study(self, study_id: str) -> list[MosAuditEvent]:
        """Return events for a study id."""
        with self._mos_lock:
            return [e for e in self._mos_events if e.resource_id == study_id]


E_GLOBAL_AUDIT = MosAuditTrailBuffer()
