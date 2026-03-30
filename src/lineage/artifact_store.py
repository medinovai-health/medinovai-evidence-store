"""Artifact version DTO (metadata lives in PostgreSQL via `Artifact` ORM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MosArtifactVersion:
    """One immutable artifact version row (reference shape for lineage helpers)."""

    logical_id: str
    version: int
    study_id: str
    artifact_type: str
    checksum_sha256: str
    storage_path: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
