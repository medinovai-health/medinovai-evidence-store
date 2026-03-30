"""Directed provenance graph for artifact derivation (scaffold, in-memory)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4


@dataclass
class MosProvenanceEdge:
    """Edge from parent artifact version to child."""

    edge_id: str
    parent_artifact_id: str
    child_artifact_id: str
    tool_used: str | None
    parameters: dict[str, Any]


@dataclass
class MosProvenanceNode:
    """Registered artifact version node."""

    artifact_id: str
    version: int
    study_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MosProvenanceGraph:
    """Tenant-scoped provenance tracking."""

    def __init__(self) -> None:
        self._mos_nodes: dict[str, MosProvenanceNode] = {}
        self._mos_edges: list[MosProvenanceEdge] = []
        self._mos_lock = Lock()

    def mos_register_node(self, mos_node: MosProvenanceNode) -> None:
        """Add or replace a node keyed by artifact_id."""
        with self._mos_lock:
            self._mos_nodes[mos_node.artifact_id] = mos_node

    def mos_add_edge(self, mos_edge: MosProvenanceEdge) -> None:
        """Record derivation."""
        with self._mos_lock:
            self._mos_edges.append(mos_edge)

    def mos_ancestors(self, mos_artifact_id: str) -> list[str]:
        """Return ancestor artifact ids (BFS upstream)."""
        with self._mos_lock:
            mos_seen: set[str] = set()
            mos_frontier = [mos_artifact_id]
            mos_out: list[str] = []
            while mos_frontier:
                mos_cur = mos_frontier.pop()
                for mos_e in self._mos_edges:
                    if mos_e.child_artifact_id == mos_cur and mos_e.parent_artifact_id not in mos_seen:
                        mos_seen.add(mos_e.parent_artifact_id)
                        mos_out.append(mos_e.parent_artifact_id)
                        mos_frontier.append(mos_e.parent_artifact_id)
            return mos_out


def mos_new_edge(
    parent_id: str,
    child_id: str,
    tool_used: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> MosProvenanceEdge:
    """Factory for a provenance edge."""
    return MosProvenanceEdge(
        edge_id=str(uuid4()),
        parent_artifact_id=parent_id,
        child_artifact_id=child_id,
        tool_used=tool_used,
        parameters=parameters or {},
    )


E_DEFAULT_GRAPH = MosProvenanceGraph()
