"""Artifact provenance: DTOs and helpers; persistence is `ProvenanceRepo` (PostgreSQL)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class MosProvenanceEdge:
    """Edge from parent artifact version to child (DTO — rows live in `provenance_edges`)."""

    edge_id: str
    parent_artifact_id: str
    child_artifact_id: str
    tool_used: str | None
    parameters: dict[str, Any]


@dataclass
class MosProvenanceNode:
    """Registered artifact version node (DTO — nodes are `artifacts` rows)."""

    artifact_id: str
    version: int
    study_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


def mos_new_edge(
    parent_id: str,
    child_id: str,
    tool_used: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> MosProvenanceEdge:
    """Build a provenance edge DTO (persist via ProvenanceRepo.mos_add_edge)."""
    return MosProvenanceEdge(
        edge_id=str(uuid4()),
        parent_artifact_id=parent_id,
        child_artifact_id=child_id,
        tool_used=tool_used,
        parameters=parameters or {},
    )
