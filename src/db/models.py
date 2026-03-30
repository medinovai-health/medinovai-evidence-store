"""SQLAlchemy 2.0 async ORM models (PostgreSQL)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def mos_utc_now() -> datetime:
    """Timezone-aware UTC default for columns."""
    return datetime.now(timezone.utc)


class MosBase(DeclarativeBase):
    """Declarative base."""


# JSONB on PostgreSQL; generic JSON fallback for other dialects (e.g. local tests).
MosJsonDict = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class StudyStatus(str, enum.Enum):
    """Study lifecycle state (aligned with Temporal workflow phases)."""

    CREATED = "CREATED"
    PROTOCOL_REVIEW = "PROTOCOL_REVIEW"
    DATA_COLLECTION = "DATA_COLLECTION"
    ANALYSIS = "ANALYSIS"
    REPORT = "REPORT"
    SIGNATURE_COLLECTION = "SIGNATURE_COLLECTION"
    ARCHIVED = "ARCHIVED"


class Study(MosBase):
    """Clinical / evidence study record."""

    __tablename__ = "studies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(512), default="Untitled")
    status: Mapped[StudyStatus] = mapped_column(
        Enum(StudyStatus, name="study_status_enum", native_enum=True),
        default=StudyStatus.CREATED,
    )
    protocol_version: Mapped[str] = mapped_column(String(64), default="1.0.0")
    created_by: Mapped[str] = mapped_column(String(256), default="system")
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    temporal_workflow_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=mos_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=mos_utc_now, onupdate=mos_utc_now
    )

    artifacts: Mapped[list[Artifact]] = relationship(
        "Artifact", back_populates="study", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        "AuditEvent", back_populates="study", cascade="all, delete-orphan"
    )


class Artifact(MosBase):
    """Versioned artifact metadata (binary payload in object storage)."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(128))
    filename: Mapped[str] = mapped_column(String(512), default="")
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(MosJsonDict, default=dict)
    created_by: Mapped[str] = mapped_column(String(256), default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=mos_utc_now
    )

    study: Mapped[Study] = relationship("Study", back_populates="artifacts")
    signatures: Mapped[list[ElectronicSignature]] = relationship(
        "ElectronicSignature", back_populates="artifact", cascade="all, delete-orphan"
    )


class ElectronicSignature(MosBase):
    """Part 11 electronic signature bound to an artifact (identity, time, meaning)."""

    __tablename__ = "electronic_signatures"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), index=True
    )
    signer_id: Mapped[str] = mapped_column(String(256))
    signer_name: Mapped[str] = mapped_column(String(512))
    signer_role: Mapped[str] = mapped_column(String(128), default="")
    meaning: Mapped[str] = mapped_column(String(256))
    signature_hash: Mapped[str] = mapped_column(String(128))
    algorithm: Mapped[str] = mapped_column(String(64), default="SHA-256")
    # Part 11: identity + timestamp + meaning (column `signed_at` in DB).
    signed_at: Mapped[datetime] = mapped_column(
        "signed_at", DateTime(timezone=True), default=mos_utc_now
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    artifact: Mapped[Artifact] = relationship("Artifact", back_populates="signatures")

    @property
    def timestamp(self) -> datetime:
        """Part 11 signing time (alias of signed_at)."""
        return self.signed_at


class AuditEvent(MosBase):
    """Immutable audit trail row (21 CFR Part 11 / ISO traceability)."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[str] = mapped_column(String(256))
    action: Mapped[str] = mapped_column(String(128))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(128))
    old_value_json: Mapped[dict[str, Any] | None] = mapped_column(
        MosJsonDict, nullable=True
    )
    new_value_json: Mapped[dict[str, Any] | None] = mapped_column(
        MosJsonDict, nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, default="")
    event_at: Mapped[datetime] = mapped_column(
        "event_at", DateTime(timezone=True), default=mos_utc_now
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    study: Mapped[Study] = relationship("Study", back_populates="audit_events")

    @property
    def timestamp(self) -> datetime:
        """Audit event time (alias of event_at)."""
        return self.event_at


class ProvenanceEdge(MosBase):
    """Persisted artifact derivation edge (PostgreSQL lineage graph)."""

    __tablename__ = "provenance_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), index=True
    )
    parent_artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), index=True
    )
    child_artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), index=True
    )
    tool_used: Mapped[str | None] = mapped_column(String(256), nullable=True)
    parameters_json: Mapped[dict[str, Any]] = mapped_column(MosJsonDict, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=mos_utc_now
    )
