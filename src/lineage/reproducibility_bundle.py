"""Exportable reproducibility bundle for FDA / study reconstruction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class MosReproducibilityBundle:
    """Manifest linking workflow run, artifacts, and hashes."""

    bundle_id: str
    study_id: str
    temporal_workflow_id: str
    temporal_run_id: str
    created_at_utc: str
    artifact_manifest: list[dict[str, Any]]
    provenance_summary: dict[str, Any]


def mos_build_bundle(
    bundle_id: str,
    study_id: str,
    temporal_workflow_id: str,
    temporal_run_id: str,
    artifact_manifest: list[dict[str, Any]],
    provenance_summary: dict[str, Any],
) -> MosReproducibilityBundle:
    """Assemble a bundle DTO."""
    return MosReproducibilityBundle(
        bundle_id=bundle_id,
        study_id=study_id,
        temporal_workflow_id=temporal_workflow_id,
        temporal_run_id=temporal_run_id,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        artifact_manifest=artifact_manifest,
        provenance_summary=provenance_summary,
    )


def mos_bundle_to_json_ready(mos_b: MosReproducibilityBundle) -> dict[str, Any]:
    """Serialize for API response."""
    return {
        "bundle_id": mos_b.bundle_id,
        "study_id": mos_b.study_id,
        "temporal_workflow_id": mos_b.temporal_workflow_id,
        "temporal_run_id": mos_b.temporal_run_id,
        "created_at_utc": mos_b.created_at_utc,
        "artifact_manifest": mos_b.artifact_manifest,
        "provenance_summary": mos_b.provenance_summary,
    }
