"""Initial evidence store schema (studies, artifacts, signatures, audit)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20250330_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

study_status_enum = postgresql.ENUM(
    "CREATED",
    "PROTOCOL_REVIEW",
    "DATA_COLLECTION",
    "ANALYSIS",
    "REPORT",
    "SIGNATURE_COLLECTION",
    "ARCHIVED",
    name="study_status_enum",
    create_type=True,
)


def upgrade() -> None:
    study_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "studies",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("status", study_status_enum, nullable=False),
        sa.Column("protocol_version", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=256), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("temporal_workflow_id", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_studies_tenant_id", "studies", ["tenant_id"], unique=False)
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("study_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=128), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column(
            "metadata_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifacts_study_id", "artifacts", ["study_id"], unique=False)
    op.create_table(
        "electronic_signatures",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("artifact_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("signer_id", sa.String(length=256), nullable=False),
        sa.Column("signer_name", sa.String(length=512), nullable=False),
        sa.Column("signer_role", sa.String(length=128), nullable=False),
        sa.Column("meaning", sa.String(length=256), nullable=False),
        sa.Column("signature_hash", sa.String(length=128), nullable=False),
        sa.Column("algorithm", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_electronic_signatures_artifact_id",
        "electronic_signatures",
        ["artifact_id"],
        unique=False,
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("study_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_id", sa.String(length=256), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column(
            "old_value_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "new_value_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_study_id", "audit_events", ["study_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_study_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_electronic_signatures_artifact_id", table_name="electronic_signatures")
    op.drop_table("electronic_signatures")
    op.drop_index("ix_artifacts_study_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_studies_tenant_id", table_name="studies")
    op.drop_table("studies")
    study_status_enum.drop(op.get_bind(), checkfirst=True)
