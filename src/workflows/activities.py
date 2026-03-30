"""Temporal activities — database-backed study lifecycle (Part 11 audit on state changes)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio import activity

from src.db.connection import mos_async_session_maker
from src.db.models import Artifact, StudyStatus
from src.db.repository import (
    ArtifactRepo,
    E_EMPTY_SHA256,
    E_STUDY_MANIFEST_TYPE,
    StudyRepo,
)

mos_logger = structlog.get_logger()

E_ACTIVITY_CREATE_STUDY = "create_study"
E_ACTIVITY_UPLOAD_ARTIFACT = "upload_artifact"
E_ACTIVITY_VERIFY_INTEGRITY = "verify_integrity"
E_ACTIVITY_COLLECT_SIGNATURE = "collect_signature"
E_ACTIVITY_ARCHIVE_STUDY = "archive_study"


@dataclass
class MosCreateStudyActivityInput:
    """Input for create / status-advance activity."""

    study_id: str
    tenant_id: str
    correlation_id: str
    workflow_id: str
    title: str = "Untitled"
    protocol_version: str = "1.0.0"
    created_by: str = "temporal_activity"
    # If set, only transition study status (study row must exist).
    target_status: str | None = None


@dataclass
class MosUploadArtifactActivityInput:
    """Register artifact metadata and advance study phase."""

    study_id: str
    tenant_id: str
    correlation_id: str
    artifact_type: str
    filename: str
    storage_path: str | None
    sha256_hash: str
    size_bytes: int
    mime_type: str
    logical_artifact_id: str | None
    created_by: str
    after_upload_status: str


@dataclass
class MosVerifyIntegrityActivityInput:
    """Verify artifact hash (and optional file read) then move to ANALYSIS."""

    study_id: str
    tenant_id: str
    correlation_id: str
    artifact_id: str
    expected_sha256: str
    actor_id: str = "integrity_checker"


@dataclass
class MosCollectSignatureActivityInput:
    """Finalize signature-collection phase after API-recorded signatures."""

    study_id: str
    tenant_id: str
    correlation_id: str
    actor_id: str = "temporal_activity"


@dataclass
class MosArchiveStudyActivityInput:
    """Archive study (terminal state)."""

    study_id: str
    tenant_id: str
    correlation_id: str
    actor_id: str = "temporal_activity"


T_sess = TypeVar("T_sess")


async def _mos_commit_session_return(
    mos_fn: Callable[[AsyncSession], Awaitable[T_sess]],
) -> T_sess:
    """Run callback in a committed transaction and return its result."""
    if mos_async_session_maker is None:
        raise RuntimeError("Database session factory not initialized")
    async with mos_async_session_maker() as mos_session:
        async with mos_session.begin():
            return await mos_fn(mos_session)


def mos_default_activity_timeouts() -> dict[str, Any]:
    """Default start-to-close timeouts per activity name."""
    from datetime import timedelta

    return {
        E_ACTIVITY_CREATE_STUDY: timedelta(seconds=30),
        E_ACTIVITY_UPLOAD_ARTIFACT: timedelta(minutes=5),
        E_ACTIVITY_VERIFY_INTEGRITY: timedelta(minutes=15),
        E_ACTIVITY_COLLECT_SIGNATURE: timedelta(seconds=60),
        E_ACTIVITY_ARCHIVE_STUDY: timedelta(seconds=60),
    }


@activity.defn(name=E_ACTIVITY_CREATE_STUDY)
async def mos_activity_create_study(mos_input: MosCreateStudyActivityInput) -> str:
    """Create study row or advance status; each transition emits AuditEvent."""
    mos_sid = UUID(mos_input.study_id)

    async def mos_work(mos_session: AsyncSession) -> None:
        mos_repo = StudyRepo(mos_session)
        if mos_input.target_status:
            mos_new = StudyStatus(mos_input.target_status)
            await mos_repo.mos_update_status(
                study_id=mos_sid,
                new_status=mos_new,
                actor_id=mos_input.created_by,
                reason=f"workflow_advance:{mos_new.value}",
                correlation_id=mos_input.correlation_id,
            )
            return
        mos_existing = await mos_repo.mos_get(mos_sid)
        if mos_existing is None:
            await mos_repo.mos_create(
                study_id=mos_sid,
                tenant_id=mos_input.tenant_id,
                title=mos_input.title,
                protocol_version=mos_input.protocol_version,
                created_by=mos_input.created_by,
                temporal_workflow_id=mos_input.workflow_id,
                correlation_id=mos_input.correlation_id,
            )

    await _mos_commit_session_return(mos_work)
    mos_logger.info(
        "activity_create_study",
        study_id=mos_input.study_id,
        target_status=mos_input.target_status,
        phi_safe=True,
    )
    return f"study_ok:{mos_input.study_id}"


@activity.defn(name=E_ACTIVITY_UPLOAD_ARTIFACT)
async def mos_activity_upload_artifact(mos_input: MosUploadArtifactActivityInput) -> str:
    """Persist artifact metadata; advance study to after_upload_status. Returns artifact UUID."""
    mos_sid = UUID(mos_input.study_id)
    mos_logical = (
        UUID(mos_input.logical_artifact_id) if mos_input.logical_artifact_id else None
    )
    mos_next = StudyStatus(mos_input.after_upload_status)

    async def mos_work(mos_session: AsyncSession) -> str:
        mos_artifact_repo = ArtifactRepo(mos_session)
        mos_art = await mos_artifact_repo.mos_register(
            study_id=mos_sid,
            artifact_type=mos_input.artifact_type,
            filename=mos_input.filename,
            storage_path=mos_input.storage_path,
            sha256_hash=mos_input.sha256_hash,
            size_bytes=mos_input.size_bytes,
            mime_type=mos_input.mime_type,
            metadata_json={"tenant_id": mos_input.tenant_id},
            created_by=mos_input.created_by,
            logical_artifact_id=mos_logical,
            correlation_id=mos_input.correlation_id,
        )
        mos_study_repo = StudyRepo(mos_session)
        await mos_study_repo.mos_update_status(
            study_id=mos_sid,
            new_status=mos_next,
            actor_id=mos_input.created_by,
            reason=f"upload_artifact:{mos_input.artifact_type}",
            correlation_id=mos_input.correlation_id,
        )
        return str(mos_art.id)

    mos_artifact_id = await _mos_commit_session_return(mos_work)
    mos_logger.info(
        "activity_upload_artifact",
        study_id=mos_input.study_id,
        phi_safe=True,
    )
    return mos_artifact_id


@activity.defn(name=E_ACTIVITY_VERIFY_INTEGRITY)
async def mos_activity_verify_integrity(
    mos_input: MosVerifyIntegrityActivityInput,
) -> str:
    """Verify stored hash matches expected (optional file read)."""
    mos_sid = UUID(mos_input.study_id)
    mos_aid = UUID(mos_input.artifact_id)

    async def mos_work(mos_session: AsyncSession) -> None:
        mos_ar = ArtifactRepo(mos_session)
        mos_art = await mos_ar.mos_get(mos_aid)
        if mos_art is None:
            raise ValueError("artifact not found for integrity check")
        mos_computed = mos_art.sha256_hash
        if mos_art.storage_path and Path(mos_art.storage_path).is_file():
            mos_data = Path(mos_art.storage_path).read_bytes()
            mos_computed = hashlib.sha256(mos_data).hexdigest()
        if mos_computed.lower() != mos_input.expected_sha256.lower():
            raise ValueError("sha256 mismatch — integrity failure")
        mos_sr = StudyRepo(mos_session)
        await mos_sr.mos_update_status(
            study_id=mos_sid,
            new_status=StudyStatus.ANALYSIS,
            actor_id=mos_input.actor_id,
            reason="verify_integrity_passed",
            correlation_id=mos_input.correlation_id,
        )

    await _mos_commit_session_return(mos_work)
    activity.heartbeat("integrity_ok")
    mos_logger.info(
        "activity_verify_integrity",
        study_id=mos_input.study_id,
        phi_safe=True,
    )
    return f"integrity_ok:{mos_input.study_id}"


@activity.defn(name=E_ACTIVITY_COLLECT_SIGNATURE)
async def mos_activity_collect_signature(
    mos_input: MosCollectSignatureActivityInput,
) -> str:
    """Enter SIGNATURE_COLLECTION; confirms manifest exists (signatures via API)."""
    mos_sid = UUID(mos_input.study_id)

    async def mos_work(mos_session: AsyncSession) -> None:
        mos_sr = StudyRepo(mos_session)
        mos_study = await mos_sr.mos_get(mos_sid)
        if mos_study is None:
            raise ValueError("study not found")
        mos_stmt_repo = ArtifactRepo(mos_session)
        mos_q = await mos_session.execute(
            select(Artifact).where(
                Artifact.study_id == mos_sid,
                Artifact.artifact_type == E_STUDY_MANIFEST_TYPE,
            )
        )
        if mos_q.scalar_one_or_none() is None:
            await mos_stmt_repo.mos_register(
                study_id=mos_sid,
                artifact_type=E_STUDY_MANIFEST_TYPE,
                filename="study_manifest.json",
                storage_path=None,
                sha256_hash=E_EMPTY_SHA256,
                size_bytes=0,
                mime_type="application/json",
                metadata_json={"purpose": "part11_binding_auto"},
                created_by=mos_input.actor_id,
                logical_artifact_id=None,
                correlation_id=mos_input.correlation_id,
            )
        await mos_sr.mos_update_status(
            study_id=mos_sid,
            new_status=StudyStatus.SIGNATURE_COLLECTION,
            actor_id=mos_input.actor_id,
            reason="signature_collection_phase",
            correlation_id=mos_input.correlation_id,
        )

    await _mos_commit_session_return(mos_work)
    mos_logger.info(
        "activity_collect_signature",
        study_id=mos_input.study_id,
        phi_safe=True,
    )
    return f"signatures_phase_ok:{mos_input.study_id}"


@activity.defn(name=E_ACTIVITY_ARCHIVE_STUDY)
async def mos_activity_archive_study(mos_input: MosArchiveStudyActivityInput) -> str:
    """Set study ARCHIVED (WORM / long-term retention hook)."""
    mos_sid = UUID(mos_input.study_id)

    async def mos_work(mos_session: AsyncSession) -> None:
        mos_sr = StudyRepo(mos_session)
        await mos_sr.mos_update_status(
            study_id=mos_sid,
            new_status=StudyStatus.ARCHIVED,
            actor_id=mos_input.actor_id,
            reason="archive_study",
            correlation_id=mos_input.correlation_id,
        )

    await _mos_commit_session_return(mos_work)
    mos_logger.info(
        "activity_archive_study",
        study_id=mos_input.study_id,
        phi_safe=True,
    )
    return f"archived:{mos_input.study_id}"
