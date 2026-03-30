"""Async repositories (study, artifact, signature, audit)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    Artifact,
    AuditEvent,
    ElectronicSignature,
    ProvenanceEdge,
    Study,
    StudyStatus,
)

E_RESOURCE_STUDY = "STUDY"
E_RESOURCE_ARTIFACT = "ARTIFACT"
E_RESOURCE_PROVENANCE = "PROVENANCE_EDGE"
E_STUDY_MANIFEST_TYPE = "STUDY_MANIFEST"
E_EMPTY_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
E_ACTION_STATE_CHANGE = "STUDY_STATE_CHANGE"
E_ACTION_ARTIFACT_REGISTERED = "ARTIFACT_REGISTERED"
E_ACTION_SIGNATURE_RECORDED = "ELECTRONIC_SIGNATURE_RECORDED"
E_ACTION_PROVENANCE_ADDED = "PROVENANCE_EDGE_ADDED"


def mos_utc_now() -> datetime:
    """UTC now for audit timestamps."""
    return datetime.now(timezone.utc)


class StudyRepo:
    """Study persistence and lifecycle status with mandatory audit rows."""

    def __init__(self, mos_session: AsyncSession) -> None:
        self._mos_session = mos_session

    async def mos_get(self, mos_study_id: uuid.UUID) -> Study | None:
        """Load study by primary key."""
        return await self._mos_session.get(Study, mos_study_id)

    async def mos_create(
        self,
        *,
        study_id: uuid.UUID,
        tenant_id: str,
        title: str,
        protocol_version: str,
        created_by: str,
        temporal_workflow_id: str | None,
        correlation_id: str,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> Study:
        """Insert study in CREATED state and audit STUDY_CREATED."""
        mos_study = Study(
            id=study_id,
            tenant_id=tenant_id,
            title=title,
            status=StudyStatus.CREATED,
            protocol_version=protocol_version,
            created_by=created_by,
            temporal_workflow_id=temporal_workflow_id,
        )
        self._mos_session.add(mos_study)
        await self._mos_session.flush()
        await AuditRepo(self._mos_session).mos_append(
            study_id=study_id,
            actor_id=created_by,
            action="STUDY_CREATED",
            resource_type=E_RESOURCE_STUDY,
            resource_id=str(study_id),
            old_value_json=None,
            new_value_json={
                "status": StudyStatus.CREATED.value,
                "correlation_id": correlation_id,
            },
            reason="study_insert",
            ip_address=ip_address,
            session_id=session_id,
        )
        mos_ar = ArtifactRepo(self._mos_session)
        await mos_ar.mos_register(
            study_id=study_id,
            artifact_type=E_STUDY_MANIFEST_TYPE,
            filename="study_manifest.json",
            storage_path=None,
            sha256_hash=E_EMPTY_SHA256,
            size_bytes=0,
            mime_type="application/json",
            metadata_json={"purpose": "part11_binding"},
            created_by=created_by,
            logical_artifact_id=None,
            correlation_id=correlation_id,
        )
        return mos_study

    async def mos_update_status(
        self,
        *,
        study_id: uuid.UUID,
        new_status: StudyStatus,
        actor_id: str,
        reason: str,
        correlation_id: str,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> Study | None:
        """Transition study status; always writes AuditEvent (Part 11 traceability)."""
        mos_study = await self.mos_get(study_id)
        if mos_study is None:
            return None
        mos_old = mos_study.status.value
        mos_study.status = new_status
        mos_study.updated_at = mos_utc_now()
        await self._mos_session.flush()
        await AuditRepo(self._mos_session).mos_append(
            study_id=study_id,
            actor_id=actor_id,
            action=E_ACTION_STATE_CHANGE,
            resource_type=E_RESOURCE_STUDY,
            resource_id=str(study_id),
            old_value_json={"status": mos_old},
            new_value_json={
                "status": new_status.value,
                "correlation_id": correlation_id,
            },
            reason=reason,
            ip_address=ip_address,
            session_id=session_id,
        )
        return mos_study


class ArtifactRepo:
    """Artifact metadata CRUD and version listing by logical group."""

    def __init__(self, mos_session: AsyncSession) -> None:
        self._mos_session = mos_session

    async def mos_register(
        self,
        *,
        study_id: uuid.UUID,
        artifact_type: str,
        filename: str,
        storage_path: str | None,
        sha256_hash: str,
        size_bytes: int,
        mime_type: str,
        metadata_json: dict[str, Any],
        created_by: str,
        logical_artifact_id: uuid.UUID | None,
        correlation_id: str,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> Artifact:
        """Insert artifact; ensures logical_artifact_id in metadata for versioning."""
        mos_meta = dict(metadata_json)
        mos_lid = logical_artifact_id or uuid.uuid4()
        mos_meta.setdefault("logical_artifact_id", str(mos_lid))
        mos_art = Artifact(
            study_id=study_id,
            artifact_type=artifact_type,
            filename=filename,
            storage_path=storage_path,
            sha256_hash=sha256_hash,
            size_bytes=size_bytes,
            mime_type=mime_type,
            metadata_json=mos_meta,
            created_by=created_by,
        )
        self._mos_session.add(mos_art)
        await self._mos_session.flush()
        await AuditRepo(self._mos_session).mos_append(
            study_id=study_id,
            actor_id=created_by,
            action=E_ACTION_ARTIFACT_REGISTERED,
            resource_type=E_RESOURCE_ARTIFACT,
            resource_id=str(mos_art.id),
            old_value_json=None,
            new_value_json={
                "artifact_type": artifact_type,
                "sha256_hash": sha256_hash,
                "logical_artifact_id": mos_meta["logical_artifact_id"],
                "correlation_id": correlation_id,
            },
            reason="artifact_register",
            ip_address=ip_address,
            session_id=session_id,
        )
        return mos_art

    async def mos_list_by_logical_id(
        self, mos_logical_id: str
    ) -> Sequence[Artifact]:
        """Return all artifact versions sharing logical_artifact_id in metadata."""
        mos_stmt: Select[tuple[Artifact]] = select(Artifact).where(
            Artifact.metadata_json["logical_artifact_id"].as_string() == mos_logical_id
        )
        mos_result = await self._mos_session.execute(mos_stmt)
        return mos_result.scalars().all()

    async def mos_get(self, mos_artifact_id: uuid.UUID) -> Artifact | None:
        """Load artifact by id."""
        return await self._mos_session.get(Artifact, mos_artifact_id)

    async def mos_find_study_manifest(self, mos_study_id: uuid.UUID) -> Artifact | None:
        """Return Part 11 manifest row for a study, if present."""
        mos_stmt = (
            select(Artifact)
            .where(
                Artifact.study_id == mos_study_id,
                Artifact.artifact_type == E_STUDY_MANIFEST_TYPE,
            )
            .limit(1)
        )
        mos_result = await self._mos_session.execute(mos_stmt)
        return mos_result.scalar_one_or_none()


class SignatureRepo:
    """Part 11 electronic signatures (identity, timestamp, meaning)."""

    def __init__(self, mos_session: AsyncSession) -> None:
        self._mos_session = mos_session

    async def mos_record(
        self,
        *,
        artifact_id: uuid.UUID,
        study_id: uuid.UUID,
        signer_id: str,
        signer_name: str,
        signer_role: str,
        meaning: str,
        signature_hash: str,
        algorithm: str,
        signed_at: datetime,
        ip_address: str | None,
        correlation_id: str,
        session_id: str | None = None,
    ) -> ElectronicSignature:
        """Persist signature and audit (identity + timestamp + meaning)."""
        mos_row = ElectronicSignature(
            artifact_id=artifact_id,
            signer_id=signer_id,
            signer_name=signer_name,
            signer_role=signer_role,
            meaning=meaning,
            signature_hash=signature_hash,
            algorithm=algorithm,
            signed_at=signed_at,
            ip_address=ip_address,
        )
        self._mos_session.add(mos_row)
        await self._mos_session.flush()
        await AuditRepo(self._mos_session).mos_append(
            study_id=study_id,
            actor_id=signer_id,
            action=E_ACTION_SIGNATURE_RECORDED,
            resource_type=E_RESOURCE_ARTIFACT,
            resource_id=str(artifact_id),
            old_value_json=None,
            new_value_json={
                "signature_id": str(mos_row.id),
                "meaning": meaning,
                "algorithm": algorithm,
                "correlation_id": correlation_id,
            },
            reason="electronic_signature",
            ip_address=ip_address,
            session_id=session_id,
        )
        return mos_row


class AuditRepo:
    """Append-only audit events."""

    def __init__(self, mos_session: AsyncSession) -> None:
        self._mos_session = mos_session

    async def mos_append(
        self,
        *,
        study_id: uuid.UUID,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        old_value_json: dict[str, Any] | None,
        new_value_json: dict[str, Any] | None,
        reason: str,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> AuditEvent:
        """Insert audit row (no updates)."""
        mos_ev = AuditEvent(
            study_id=study_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value_json=old_value_json,
            new_value_json=new_value_json,
            reason=reason,
            ip_address=ip_address,
            session_id=session_id,
        )
        self._mos_session.add(mos_ev)
        await self._mos_session.flush()
        return mos_ev

    async def mos_list_for_study(self, mos_study_id: uuid.UUID) -> Sequence[AuditEvent]:
        """All audit events for a study, newest last."""
        mos_stmt = (
            select(AuditEvent)
            .where(AuditEvent.study_id == mos_study_id)
            .order_by(AuditEvent.event_at.asc())
        )
        mos_result = await self._mos_session.execute(mos_stmt)
        return mos_result.scalars().all()


class ProvenanceRepo:
    """Artifact derivation edges (PostgreSQL-backed lineage)."""

    def __init__(self, mos_session: AsyncSession) -> None:
        self._mos_session = mos_session

    async def mos_add_edge(
        self,
        *,
        study_id: uuid.UUID,
        parent_artifact_id: uuid.UUID,
        child_artifact_id: uuid.UUID,
        tool_used: str | None,
        parameters_json: dict[str, Any],
        actor_id: str,
        correlation_id: str,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> ProvenanceEdge:
        """Insert provenance edge and audit row."""
        mos_row = ProvenanceEdge(
            study_id=study_id,
            parent_artifact_id=parent_artifact_id,
            child_artifact_id=child_artifact_id,
            tool_used=tool_used,
            parameters_json=parameters_json,
        )
        self._mos_session.add(mos_row)
        await self._mos_session.flush()
        await AuditRepo(self._mos_session).mos_append(
            study_id=study_id,
            actor_id=actor_id,
            action=E_ACTION_PROVENANCE_ADDED,
            resource_type=E_RESOURCE_PROVENANCE,
            resource_id=str(mos_row.id),
            old_value_json=None,
            new_value_json={
                "parent_artifact_id": str(parent_artifact_id),
                "child_artifact_id": str(child_artifact_id),
                "correlation_id": correlation_id,
            },
            reason="provenance_edge",
            ip_address=ip_address,
            session_id=session_id,
        )
        return mos_row

    async def mos_list_edges_for_study(
        self, mos_study_id: uuid.UUID
    ) -> Sequence[ProvenanceEdge]:
        """All provenance edges in a study."""
        mos_stmt = select(ProvenanceEdge).where(
            ProvenanceEdge.study_id == mos_study_id
        )
        mos_result = await self._mos_session.execute(mos_stmt)
        return mos_result.scalars().all()

    async def mos_ancestors(self, mos_artifact_id: uuid.UUID) -> list[str]:
        """Parent artifact ids upstream of child (BFS), persisted graph only."""
        mos_seen: set[uuid.UUID] = set()
        mos_out: list[str] = []
        mos_frontier: list[uuid.UUID] = [mos_artifact_id]
        while mos_frontier:
            mos_cur = mos_frontier.pop()
            mos_stmt = select(ProvenanceEdge).where(
                ProvenanceEdge.child_artifact_id == mos_cur
            )
            mos_result = await self._mos_session.execute(mos_stmt)
            for mos_e in mos_result.scalars().all():
                mos_pid = mos_e.parent_artifact_id
                if mos_pid not in mos_seen:
                    mos_seen.add(mos_pid)
                    mos_out.append(str(mos_pid))
                    mos_frontier.append(mos_pid)
        return mos_out
