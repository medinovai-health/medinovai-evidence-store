"""Electronic signature and workflow transition signaling."""

from __future__ import annotations

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from temporalio.client import Client
from temporalio.exceptions import TemporalError

from src.api.deps import (
    mos_get_db_session,
    mos_get_settings_dep,
    mos_get_temporal_client,
)
from src.compliance.electronic_signature import (
    MosElectronicSignature,
    mos_build_signature_hash,
    mos_validate_signature_payload,
)
from src.db.repository import ArtifactRepo, SignatureRepo, StudyRepo
from src.settings import MosSettings
from src.workflows.study_lifecycle import StudyLifecycleWorkflow

router = APIRouter(prefix="/api/v1/signatures", tags=["signatures"])


class MosSignatureSubmitBody(BaseModel):
    """Signature capture payload."""

    study_id: str
    workflow_id: str | None = None
    artifact_id: str | None = None
    transition_id: str = Field(
        ...,
        description=(
            "Must match study_lifecycle transition (e.g. after_study_creation)."
        ),
    )
    signature: MosElectronicSignature


@router.post("/submit")
async def mos_submit_signature(
    mos_body: MosSignatureSubmitBody,
    mos_request: Request,
    mos_session: Annotated[AsyncSession, Depends(mos_get_db_session)],
    mos_temporal: Annotated[Client | None, Depends(mos_get_temporal_client)],
    mos_settings: Annotated[MosSettings, Depends(mos_get_settings_dep)],
) -> dict[str, Any]:
    """Validate Part 11 fields, persist signature + audit, signal workflow."""
    mos_summary = mos_validate_signature_payload(mos_body.signature)
    try:
        mos_sid = uuid.UUID(mos_body.study_id)
    except ValueError as mos_exc:
        raise HTTPException(status_code=400, detail="invalid study_id") from mos_exc
    mos_study = await StudyRepo(mos_session).mos_get(mos_sid)
    if not mos_study:
        raise HTTPException(status_code=404, detail="study not found")
    mos_wf = mos_body.workflow_id or mos_study.temporal_workflow_id
    if not mos_wf:
        raise HTTPException(status_code=400, detail="workflow_id required")
    mos_ar = ArtifactRepo(mos_session)
    mos_artifact_id: uuid.UUID
    if mos_body.artifact_id:
        try:
            mos_artifact_id = uuid.UUID(mos_body.artifact_id)
        except ValueError as mos_exc:
            raise HTTPException(status_code=400, detail="invalid artifact_id") from mos_exc
        mos_art = await mos_ar.mos_get(mos_artifact_id)
        if not mos_art or mos_art.study_id != mos_sid:
            raise HTTPException(status_code=400, detail="artifact not in study")
    else:
        mos_manifest = await mos_ar.mos_find_study_manifest(mos_sid)
        if not mos_manifest:
            raise HTTPException(status_code=400, detail="study manifest not found")
        mos_artifact_id = mos_manifest.id
    mos_ip = mos_request.client.host if mos_request.client else None
    mos_hash_payload = {
        "signer_id": mos_body.signature.signer_id,
        "signer_name": mos_body.signature.signer_name,
        "meaning": mos_body.signature.meaning.value,
        "timestamp": mos_body.signature.timestamp.isoformat(),
        "intent_statement": mos_body.signature.intent_statement,
        "record_checksum_sha256": mos_body.signature.record_checksum_sha256,
        "transition_id": mos_body.transition_id,
    }
    mos_sig_hash = mos_build_signature_hash(mos_hash_payload)
    await SignatureRepo(mos_session).mos_record(
        artifact_id=mos_artifact_id,
        study_id=mos_sid,
        signer_id=mos_body.signature.signer_id,
        signer_name=mos_body.signature.signer_name,
        signer_role=mos_body.signature.signer_role,
        meaning=mos_body.signature.meaning.value,
        signature_hash=mos_sig_hash,
        algorithm="SHA-256",
        signed_at=mos_body.signature.timestamp,
        ip_address=mos_ip,
        correlation_id=mos_body.signature.signature_id,
        session_id=mos_request.headers.get("X-Session-Id"),
    )
    await mos_session.commit()
    if mos_temporal is None or os.getenv("MOS_SKIP_TEMPORAL", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        return {**mos_summary, "temporal_signal": "skipped"}
    try:
        mos_handle = mos_temporal.get_workflow_handle(mos_wf)
        await mos_handle.signal(
            StudyLifecycleWorkflow.mos_submit_transition_signature,
            mos_body.transition_id,
        )
    except (TemporalError, OSError, RuntimeError) as mos_exc:
        raise HTTPException(
            status_code=502,
            detail=f"temporal signal failed: {mos_exc!s}",
        ) from mos_exc
    return {**mos_summary, "temporal_signal": "sent", "workflow_id": mos_wf}
