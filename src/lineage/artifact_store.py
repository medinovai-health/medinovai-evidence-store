"""Versioned artifact metadata store (scaffold; binary blobs in external object store)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4


@dataclass
class MosArtifactVersion:
    """One immutable artifact version row."""

    logical_id: str
    version: int
    study_id: str
    artifact_type: str
    checksum_sha256: str
    storage_path: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


class MosArtifactStore:
    """In-memory version table keyed by logical_id -> ordered versions."""

    def __init__(self) -> None:
        self._mos_by_logical: dict[str, list[MosArtifactVersion]] = {}
        self._mos_lock = Lock()

    def mos_put(self, mos_art: MosArtifactVersion) -> MosArtifactVersion:
        """Append a new version for logical_id."""
        with self._mos_lock:
            mos_list = self._mos_by_logical.setdefault(mos_art.logical_id, [])
            mos_list.append(mos_art)
        return mos_art

    def mos_list_versions(self, mos_logical_id: str) -> list[MosArtifactVersion]:
        """Return all versions for an artifact."""
        with self._mos_lock:
            return list(self._mos_by_logical.get(mos_logical_id, []))

    def mos_next_version(self, mos_logical_id: str) -> int:
        """Monotonic version counter."""
        with self._mos_lock:
            mos_list = self._mos_by_logical.get(mos_logical_id, [])
            return len(mos_list) + 1


def mos_new_artifact(
    study_id: str,
    artifact_type: str,
    checksum_sha256: str,
    storage_path: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> MosArtifactVersion:
    """Create version 1 artifact with generated logical id."""
    mos_lid = str(uuid4())
    return MosArtifactVersion(
        logical_id=mos_lid,
        version=1,
        study_id=study_id,
        artifact_type=artifact_type,
        checksum_sha256=checksum_sha256,
        storage_path=storage_path,
        metadata=metadata or {},
    )


E_DEFAULT_ARTIFACT_STORE = MosArtifactStore()
