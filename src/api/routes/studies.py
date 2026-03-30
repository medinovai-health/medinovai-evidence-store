"""Study management API."""

from __future__ import annotations

import os
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client
from temporalio.exceptions import TemporalError

from src.api.deps import (
    mos_get_db_session,
    mos_get_settings_dep,
    mos_get_temporal_client,
    mos_tenant_header,
)
from src.db.repository import StudyRepo
from src.settings import MosSettings
from src.workflows.study_lifecycle import MosStudyLifecycleInput, StudyLifecycleWorkflow

router = APIRouter(prefix="/api/v1/studies", tags=["studies"])


@router.post("")
async def mos_create_study(
    mos_tenant_id: Annotated[str, Depends(mos_tenant_header)],
    mos_session: Annotated[AsyncSession, Depends(mos_get_db_session)],
    mos_settings: Annotated[MosSettings, Depends(mos_get_settings_dep)],
    mos_temporal: Annotated[Client | None, Depends(mos_get_temporal_client)],
) -> dict[str, Any]:
    """Create study in PostgreSQL and start lifecycle workflow when Temporal is up."""
    mos_study_id = uuid.uuid4()
    mos_corr = str(uuid.uuid4())
    mos_wf_id = f"study-lifecycle-{mos_study_id}"
    mos_repo = StudyRepo(mos_session)
    await mos_repo.mos_create(
        study_id=mos_study_id,
        tenant_id=mos_tenant_id,
        title="Untitled",
        protocol_version="1.0.0",
        created_by="api",
        temporal_workflow_id=mos_wf_id,
        correlation_id=mos_corr,
    )
    await mos_session.commit()
    mos_wf_started: str | None = None
    if (
        mos_temporal is not None
        and os.getenv("MOS_SKIP_TEMPORAL", "").lower() not in ("1", "true", "yes")
    ):
        try:
            mos_handle = await mos_temporal.start_workflow(
                StudyLifecycleWorkflow.run,
                MosStudyLifecycleInput(
                    study_id=str(mos_study_id),
                    tenant_id=mos_tenant_id,
                    correlation_id=mos_corr,
                ),
                id=mos_wf_id,
                task_queue=mos_settings.task_queue,
            )
            mos_wf_started = mos_handle.id
        except (TemporalError, OSError, RuntimeError):
            mos_wf_started = None
    return {
        "study_id": str(mos_study_id),
        "workflow_id": mos_wf_started or mos_wf_id,
        "correlation_id": mos_corr,
    }


@router.get("/{study_id}")
async def mos_get_study(
    study_id: str,
    mos_session: Annotated[AsyncSession, Depends(mos_get_db_session)],
) -> dict[str, Any]:
    """Return study row from database."""
    try:
        mos_uid = uuid.UUID(study_id)
    except ValueError as mos_exc:
        raise HTTPException(status_code=400, detail="invalid study id") from mos_exc
    mos_rec = await StudyRepo(mos_session).mos_get(mos_uid)
    if not mos_rec:
        raise HTTPException(status_code=404, detail="study not found")
    return {
        "study_id": str(mos_rec.id),
        "tenant_id": mos_rec.tenant_id,
        "phase": mos_rec.status.value,
        "workflow_id": mos_rec.temporal_workflow_id,
        "title": mos_rec.title,
        "protocol_version": mos_rec.protocol_version,
    }
