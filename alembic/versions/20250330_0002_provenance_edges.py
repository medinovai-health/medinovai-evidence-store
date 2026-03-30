"""Provenance edges table (PostgreSQL lineage)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20250330_0002"
down_revision: Union[str, None] = "20250330_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provenance_edges",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("study_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("parent_artifact_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("child_artifact_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tool_used", sa.String(length=256), nullable=True),
        sa.Column(
            "parameters_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_artifact_id"], ["artifacts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["child_artifact_id"], ["artifacts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provenance_edges_study_id", "provenance_edges", ["study_id"], unique=False
    )
    op.create_index(
        "ix_provenance_edges_parent_artifact_id",
        "provenance_edges",
        ["parent_artifact_id"],
        unique=False,
    )
    op.create_index(
        "ix_provenance_edges_child_artifact_id",
        "provenance_edges",
        ["child_artifact_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_provenance_edges_child_artifact_id", table_name="provenance_edges")
    op.drop_index("ix_provenance_edges_parent_artifact_id", table_name="provenance_edges")
    op.drop_index("ix_provenance_edges_study_id", table_name="provenance_edges")
    op.drop_table("provenance_edges")
