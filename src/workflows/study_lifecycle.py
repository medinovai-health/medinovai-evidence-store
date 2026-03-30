"""Study lifecycle workflow — states gated by Part 11 signatures (Temporal)."""

from __future__ import annotations

from dataclasses import dataclass

from temporalio import workflow

# Phase strings MUST match StudyStatus in src.db.models (no SQLAlchemy import here —
# workflow sandbox must stay deterministic).
E_PHASE_CREATED = "CREATED"
E_PHASE_PROTOCOL_REVIEW = "PROTOCOL_REVIEW"
E_PHASE_DATA_COLLECTION = "DATA_COLLECTION"
E_PHASE_ANALYSIS = "ANALYSIS"
E_PHASE_REPORT = "REPORT"
E_PHASE_SIGNATURE_COLLECTION = "SIGNATURE_COLLECTION"
E_PHASE_ARCHIVED = "ARCHIVED"

with workflow.unsafe.imports_passed_through():
    from src.workflows import activities
    from src.workflows.activities import (
        MosArchiveStudyActivityInput,
        MosCollectSignatureActivityInput,
        MosCreateStudyActivityInput,
        MosUploadArtifactActivityInput,
        MosVerifyIntegrityActivityInput,
    )

E_WORKFLOW_NAME = "StudyLifecycleWorkflow"

E_TRANSITION_AFTER_STUDY = "after_study_creation"
E_TRANSITION_AFTER_PROTOCOL = "after_protocol_approval"
E_TRANSITION_AFTER_DATA = "after_data_collection"
E_TRANSITION_AFTER_ANALYSIS = "after_analysis"
E_TRANSITION_AFTER_REPORT = "after_report_generation"
E_TRANSITION_BEFORE_ARCHIVE = "before_archive"

# Deterministic placeholder checksums for demo activities (not PHI).
E_DEMO_DATA_SHA256 = (
    "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
)
E_DEMO_REPORT_SHA256 = (
    "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186ff76871326fb118e"
)


@dataclass
class MosStudyLifecycleInput:
    """Workflow input."""

    study_id: str
    tenant_id: str
    correlation_id: str


@workflow.defn(name=E_WORKFLOW_NAME)
class StudyLifecycleWorkflow:
    """CREATED → … → ARCHIVED with signed transitions (21 CFR Part 11)."""

    def __init__(self) -> None:
        # Workflow-local wait state (Temporal); domain state is in PostgreSQL.
        self._mos_signed: dict[str, bool] = {}
        self._mos_phase = E_PHASE_CREATED
        self._mos_study_id = ""
        self._mos_tenant_id = ""
        self._mos_correlation_id = ""
        self._mos_workflow_id = ""
        self._mos_data_artifact_id = ""
        self._mos_report_artifact_id = ""

    @workflow.query
    def mos_current_phase(self) -> str:
        """Expose phase for operators / API."""
        return self._mos_phase

    @workflow.signal
    def mos_submit_transition_signature(self, mos_transition_id: str) -> None:
        """Mark transition as signed after Part 11 capture at the API."""
        self._mos_signed[mos_transition_id] = True

    @workflow.run
    async def run(self, mos_input: MosStudyLifecycleInput) -> str:
        """Execute gated lifecycle with database-backed activities."""
        self._mos_study_id = mos_input.study_id
        self._mos_tenant_id = mos_input.tenant_id
        self._mos_correlation_id = mos_input.correlation_id
        self._mos_workflow_id = workflow.info().workflow_id
        mos_to = activities.mos_default_activity_timeouts()

        self._mos_phase = E_PHASE_CREATED
        await workflow.execute_activity(
            activities.mos_activity_create_study,
            MosCreateStudyActivityInput(
                study_id=mos_input.study_id,
                tenant_id=mos_input.tenant_id,
                correlation_id=mos_input.correlation_id,
                workflow_id=self._mos_workflow_id,
            ),
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_CREATE_STUDY],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_STUDY)

        self._mos_phase = E_PHASE_PROTOCOL_REVIEW
        await workflow.execute_activity(
            activities.mos_activity_create_study,
            MosCreateStudyActivityInput(
                study_id=mos_input.study_id,
                tenant_id=mos_input.tenant_id,
                correlation_id=mos_input.correlation_id,
                workflow_id=self._mos_workflow_id,
                target_status="PROTOCOL_REVIEW",
            ),
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_CREATE_STUDY],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_PROTOCOL)

        self._mos_phase = E_PHASE_DATA_COLLECTION
        self._mos_data_artifact_id = await workflow.execute_activity(
            activities.mos_activity_upload_artifact,
            MosUploadArtifactActivityInput(
                study_id=mos_input.study_id,
                tenant_id=mos_input.tenant_id,
                correlation_id=mos_input.correlation_id,
                artifact_type="STUDY_DATA",
                filename="dataset.bin",
                storage_path=None,
                sha256_hash=E_DEMO_DATA_SHA256,
                size_bytes=0,
                mime_type="application/octet-stream",
                logical_artifact_id=None,
                created_by="workflow",
                after_upload_status="DATA_COLLECTION",
            ),
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_UPLOAD_ARTIFACT],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_DATA)

        self._mos_phase = E_PHASE_ANALYSIS
        await workflow.execute_activity(
            activities.mos_activity_verify_integrity,
            MosVerifyIntegrityActivityInput(
                study_id=mos_input.study_id,
                tenant_id=mos_input.tenant_id,
                correlation_id=mos_input.correlation_id,
                artifact_id=self._mos_data_artifact_id,
                expected_sha256=E_DEMO_DATA_SHA256,
            ),
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_VERIFY_INTEGRITY],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_ANALYSIS)

        self._mos_phase = E_PHASE_REPORT
        self._mos_report_artifact_id = await workflow.execute_activity(
            activities.mos_activity_upload_artifact,
            MosUploadArtifactActivityInput(
                study_id=mos_input.study_id,
                tenant_id=mos_input.tenant_id,
                correlation_id=mos_input.correlation_id,
                artifact_type="STUDY_REPORT",
                filename="report.pdf",
                storage_path=None,
                sha256_hash=E_DEMO_REPORT_SHA256,
                size_bytes=0,
                mime_type="application/pdf",
                logical_artifact_id=None,
                created_by="workflow",
                after_upload_status="REPORT",
            ),
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_UPLOAD_ARTIFACT],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_REPORT)

        self._mos_phase = E_PHASE_SIGNATURE_COLLECTION
        await workflow.execute_activity(
            activities.mos_activity_collect_signature,
            MosCollectSignatureActivityInput(
                study_id=mos_input.study_id,
                tenant_id=mos_input.tenant_id,
                correlation_id=mos_input.correlation_id,
            ),
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_COLLECT_SIGNATURE],
        )
        await self._mos_wait_transition(E_TRANSITION_BEFORE_ARCHIVE)

        self._mos_phase = E_PHASE_ARCHIVED
        await workflow.execute_activity(
            activities.mos_activity_archive_study,
            MosArchiveStudyActivityInput(
                study_id=mos_input.study_id,
                tenant_id=mos_input.tenant_id,
                correlation_id=mos_input.correlation_id,
            ),
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_ARCHIVE_STUDY],
        )
        return "COMPLETED"

    async def _mos_wait_transition(self, mos_transition_id: str) -> None:
        """Block until signature signal received for transition."""
        await workflow.wait_condition(
            lambda: self._mos_signed.get(mos_transition_id, False)
        )
