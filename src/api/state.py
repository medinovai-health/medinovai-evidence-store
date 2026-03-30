"""Process-local registries (replace with DB in production)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class MosStudyRecord:
    """Study metadata and optional Temporal workflow id."""

    study_id: str
    tenant_id: str
    phase: str = "REGISTERED"
    workflow_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class MosStudyRegistry:
    """In-memory study table."""

    def __init__(self) -> None:
        self._mos_studies: dict[str, MosStudyRecord] = {}
        self._mos_lock = Lock()

    def mos_put(self, mos_rec: MosStudyRecord) -> None:
        with self._mos_lock:
            self._mos_studies[mos_rec.study_id] = mos_rec

    def mos_get(self, study_id: str) -> MosStudyRecord | None:
        with self._mos_lock:
            return self._mos_studies.get(study_id)


E_STUDY_REGISTRY = MosStudyRegistry()
