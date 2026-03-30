"""Artifact metadata endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import mos_get_db_session, mos_tenant_header
from src.compliance.data_integrity import E_HASH_ALGORITHM
from src.db.repository import ArtifactRepo

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


class MosArtifactRegisterBody(BaseModel):
    """Request body for artifact registration."""

    study_id: str
    artifact_type: str
    checksum_sha256: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    storage_path: str | None = None
    filename: str = "artifact.bin"
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0


@router.post("")
async def mos_register_artifact(
    mos_body: MosArtifactRegisterBody,
    mos_tenant_id: Annotated[str, Depends(mos_tenant_header)],
    mos_session: Annotated[AsyncSession, Depends(mos_get_db_session)],
) -> dict[str, Any]:
    """Register artifact metadata (tenant echoed for isolation audits)."""
    try:
        mos_sid = uuid.UUID(mos_body.study_id)
    except ValueError as mos_exc:
        raise HTTPException(status_code=400, detail="invalid study_id") from mos_exc
    mos_logical = uuid4()
    mos_repo = ArtifactRepo(mos_session)
    mos_av = await mos_repo.mos_register(
        study_id=mos_sid,
        artifact_type=mos_body.artifact_type,
        filename=mos_body.filename,
        storage_path=mos_body.storage_path,
        sha256_hash=mos_body.checksum_sha256,
        size_bytes=mos_body.size_bytes,
        mime_type=mos_body.mime_type,
        metadata_json={
            "tenant_id": mos_tenant_id,
            "algorithm": E_HASH_ALGORITHM,
        },
        created_by="api",
        logical_artifact_id=mos_logical,
        correlation_id=str(uuid4()),
    )
    mos_lid = mos_av.metadata_json.get("logical_artifact_id", str(mos_av.id))
    mos_versions = await mos_repo.mos_list_by_logical_id(str(mos_lid))
    mos_ver = len(mos_versions)
    return {
        "logical_id": str(mos_lid),
        "version": mos_ver,
        "study_id": mos_body.study_id,
        "phi_safe": True,
    }


@router.get("/{logical_id}/versions")
async def mos_list_versions(
    logical_id: str,
    mos_session: Annotated[AsyncSession, Depends(mos_get_db_session)],
) -> dict[str, Any]:
    """List versions for logical artifact id."""
    mos_versions = await ArtifactRepo(mos_session).mos_list_by_logical_id(logical_id)
    if not mos_versions:
        raise HTTPException(status_code=404, detail="artifact not found")
    return {
        "logical_id": logical_id,
        "versions": [
            {
                "version": idx + 1,
                "checksum_sha256": v.sha256_hash,
                "artifact_type": v.artifact_type,
            }
            for idx, v in enumerate(mos_versions)
        ],
    }
