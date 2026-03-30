"""Study management API."""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from temporalio.client import Client
from temporalio.exceptions import TemporalError

from src.api.deps import mos_tenant_header
from src.api.state import E_STUDY_REGISTRY, MosStudyRecord
from src.settings import MosSettings, mos_get_settings
from src.compliance.audit_trail import E_AUDIT_CATEGORY_STUDY, E_GLOBAL_AUDIT
from src.workflows.study_lifecycle import MosStudyLifecycleInput, MosStudyLifecycleWorkflow

router = APIRouter(prefix="/api/v1/studies", tags=["studies"])


async def mos_temporal_client(mos_settings: MosSettings = Depends(mos_get_settings)) -> Client | None:
    """Connect Temporal or return None if skipped."""
    if os.getenv("MOS_SKIP_TEMPORAL", "").lower() in ("1", "true", "yes"):
        return None
    try:
        return await Client.connect(
            mos_settings.temporal_address,
            namespace=mos_settings.temporal_namespace,
        )
    except (TemporalError, OSError, RuntimeError):
        return None


@router.post("")
async def mos_create_study(
    mos_tenant_id: str = Depends(mos_tenant_header),
    mos_client: Client | None = Depends(mos_temporal_client),
    mos_settings: MosSettings = Depends(mos_get_settings),
) -> dict[str, Any]:
    """Create study and optionally start lifecycle workflow."""
    mos_study_id = str(uuid.uuid4())
    mos_corr = str(uuid.uuid4())
    mos_wf_id: str | None = None
    if mos_client is not None:
        mos_handle = await mos_client.start_workflow(
            MosStudyLifecycleWorkflow.run,
            MosStudyLifecycleInput(
                study_id=mos_study_id,
                tenant_id=mos_tenant_id,
                correlation_id=mos_corr,
            ),
            id=f"study-lifecycle-{mos_study_id}",
            task_queue=mos_settings.task_queue,
        )
        mos_wf_id = mos_handle.id
    E_STUDY_REGISTRY.mos_put(
        MosStudyRecord(study_id=mos_study_id, tenant_id=mos_tenant_id, workflow_id=mos_wf_id)
    )
    E_GLOBAL_AUDIT.mos_append(
        actor_id="api",
        action="STUDY_REGISTERED",
        resource_type="STUDY",
        resource_id=mos_study_id,
        reason="create_study_endpoint",
        correlation_id=mos_corr,
        tenant_id=mos_tenant_id,
        category=E_AUDIT_CATEGORY_STUDY,
        metadata={"workflow_id": mos_wf_id},
    )
    return {"study_id": mos_study_id, "workflow_id": mos_wf_id, "correlation_id": mos_corr}


@router.get("/{study_id}")
async def mos_get_study(study_id: str) -> dict[str, Any]:
    """Return study record."""
    mos_rec = E_STUDY_REGISTRY.mos_get(study_id)
    if not mos_rec:
        raise HTTPException(status_code=404, detail="study not found")
    return {
        "study_id": mos_rec.study_id,
        "tenant_id": mos_rec.tenant_id,
        "phase": mos_rec.phase,
        "workflow_id": mos_rec.workflow_id,
    }
