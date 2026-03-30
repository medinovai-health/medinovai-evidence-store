"""Artifact metadata endpoints."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import mos_tenant_header
from src.compliance.data_integrity import E_HASH_ALGORITHM
from src.lineage.artifact_store import E_DEFAULT_ARTIFACT_STORE, MosArtifactVersion

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


class MosArtifactRegisterBody(BaseModel):
    """Request body for artifact registration."""

    study_id: str
    artifact_type: str
    checksum_sha256: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    storage_path: str | None = None


@router.post("")
async def mos_register_artifact(
    mos_body: MosArtifactRegisterBody,
    mos_tenant_id: str = Depends(mos_tenant_header),
) -> dict[str, Any]:
    """Register artifact metadata (tenant echoed for isolation audits)."""
    mos_logical = str(uuid4())
    mos_ver = E_DEFAULT_ARTIFACT_STORE.mos_next_version(mos_logical)
    mos_av = MosArtifactVersion(
        logical_id=mos_logical,
        version=mos_ver,
        study_id=mos_body.study_id,
        artifact_type=mos_body.artifact_type,
        checksum_sha256=mos_body.checksum_sha256,
        storage_path=mos_body.storage_path,
        metadata={"tenant_id": mos_tenant_id, "algorithm": E_HASH_ALGORITHM},
    )
    E_DEFAULT_ARTIFACT_STORE.mos_put(mos_av)
    return {
        "logical_id": mos_av.logical_id,
        "version": mos_av.version,
        "study_id": mos_av.study_id,
        "phi_safe": True,
    }


@router.get("/{logical_id}/versions")
async def mos_list_versions(logical_id: str) -> dict[str, Any]:
    """List versions for logical artifact id."""
    mos_versions = E_DEFAULT_ARTIFACT_STORE.mos_list_versions(logical_id)
    if not mos_versions:
        raise HTTPException(status_code=404, detail="artifact not found")
    return {
        "logical_id": logical_id,
        "versions": [
            {
                "version": v.version,
                "checksum_sha256": v.checksum_sha256,
                "artifact_type": v.artifact_type,
            }
            for v in mos_versions
        ],
    }
