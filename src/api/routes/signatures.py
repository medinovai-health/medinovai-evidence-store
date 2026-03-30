"""Electronic signature and workflow transition signaling."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from temporalio.client import Client
from temporalio.exceptions import TemporalError

from src.api.state import E_STUDY_REGISTRY
from src.compliance.audit_trail import (
    E_AUDIT_CATEGORY_SIGNATURE,
    E_GLOBAL_AUDIT,
)
from src.compliance.electronic_signature import (
    MosElectronicSignature,
    mos_validate_signature_payload,
)
from src.settings import MosSettings, mos_get_settings
from src.workflows.study_lifecycle import MosStudyLifecycleWorkflow

router = APIRouter(prefix="/api/v1/signatures", tags=["signatures"])


class MosSignatureSubmitBody(BaseModel):
    """Signature capture payload."""

    study_id: str
    workflow_id: str | None = None
    transition_id: str = Field(
        ...,
        description=(
            "Must match study_lifecycle transition (e.g. after_study_creation)."
        ),
    )
    signature: MosElectronicSignature


async def mos_connect_client(
    mos_settings: MosSettings = Depends(mos_get_settings),
) -> Client | None:
    """Temporal client for signaling."""
    if os.getenv("MOS_SKIP_TEMPORAL", "").lower() in ("1", "true", "yes"):
        return None
    try:
        return await Client.connect(
            mos_settings.temporal_address,
            namespace=mos_settings.temporal_namespace,
        )
    except (TemporalError, OSError, RuntimeError):
        return None


@router.post("/submit")
async def mos_submit_signature(
    mos_body: MosSignatureSubmitBody,
    mos_client: Client | None = Depends(mos_connect_client),
    mos_settings: MosSettings = Depends(mos_get_settings),
) -> dict[str, Any]:
    """Validate Part 11 fields and signal workflow transition."""
    mos_summary = mos_validate_signature_payload(mos_body.signature)
    mos_wf = mos_body.workflow_id
    if not mos_wf:
        mos_rec = E_STUDY_REGISTRY.mos_get(mos_body.study_id)
        if not mos_rec or not mos_rec.workflow_id:
            raise HTTPException(status_code=400, detail="workflow_id required")
        mos_wf = mos_rec.workflow_id
    if mos_client is None:
        E_GLOBAL_AUDIT.mos_append(
            actor_id=mos_body.signature.signer_id,
            action="SIGNATURE_RECORDED_NO_TEMPORAL",
            resource_type="STUDY",
            resource_id=mos_body.study_id,
            reason=mos_body.transition_id,
            correlation_id=mos_summary["signature_id"],
            tenant_id=mos_settings.tenant_id,
            category=E_AUDIT_CATEGORY_SIGNATURE,
            metadata=mos_summary,
        )
        return {**mos_summary, "temporal_signal": "skipped"}
    mos_handle = mos_client.get_workflow_handle(mos_wf)
    await mos_handle.signal(
        MosStudyLifecycleWorkflow.mos_submit_transition_signature,
        mos_body.transition_id,
    )
    E_GLOBAL_AUDIT.mos_append(
        actor_id=mos_body.signature.signer_id,
        action="SIGNATURE_AND_SIGNAL",
        resource_type="STUDY",
        resource_id=mos_body.study_id,
        reason=mos_body.transition_id,
        correlation_id=mos_summary["signature_id"],
        tenant_id=mos_settings.tenant_id,
        category=E_AUDIT_CATEGORY_SIGNATURE,
        metadata=mos_summary,
    )
    return {**mos_summary, "temporal_signal": "sent", "workflow_id": mos_wf}
