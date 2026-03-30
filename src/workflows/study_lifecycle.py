"""Main study lifecycle workflow — each phase gated by electronic signature."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.workflows import activities

E_WORKFLOW_NAME = "StudyLifecycleWorkflow"

E_TRANSITION_AFTER_STUDY = "after_study_creation"
E_TRANSITION_AFTER_PROTOCOL = "after_protocol_approval"
E_TRANSITION_AFTER_DATA = "after_data_collection"
E_TRANSITION_AFTER_ANALYSIS = "after_analysis"
E_TRANSITION_AFTER_REPORT = "after_report_generation"
E_TRANSITION_BEFORE_ARCHIVE = "before_archive"


@dataclass
class MosStudyLifecycleInput:
    """Workflow input."""

    study_id: str
    tenant_id: str
    correlation_id: str


@workflow.defn(name=E_WORKFLOW_NAME)
class MosStudyLifecycleWorkflow:
    """Study creation through archive with signed state transitions."""

    def __init__(self) -> None:
        self._mos_signed: dict[str, bool] = {}
        self._mos_phase = "INIT"
        self._mos_study_id = ""

    @workflow.query
    def mos_current_phase(self) -> str:
        """Expose phase for API queries."""
        return self._mos_phase

    @workflow.signal
    def mos_submit_transition_signature(self, mos_transition_id: str) -> None:
        """Mark transition as signed (client must call after Part 11 capture)."""
        self._mos_signed[mos_transition_id] = True

    @workflow.run
    async def run(self, mos_input: MosStudyLifecycleInput) -> str:
        """Execute gated lifecycle."""
        self._mos_study_id = mos_input.study_id
        mos_to = activities.mos_default_activity_timeouts()

        self._mos_phase = "CREATED"
        await workflow.execute_activity(
            activities.mos_activity_create_study,
            mos_input.study_id,
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_CREATE],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_STUDY)

        self._mos_phase = "PROTOCOL_APPROVED"
        await workflow.execute_activity(
            activities.mos_activity_record_protocol,
            mos_input.study_id,
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_PROTOCOL],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_PROTOCOL)

        self._mos_phase = "DATA_COLLECTION"
        await workflow.execute_activity(
            activities.mos_activity_collect_data,
            mos_input.study_id,
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_DATA],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_DATA)

        self._mos_phase = "ANALYSIS"
        await workflow.execute_activity(
            activities.mos_activity_run_analysis,
            mos_input.study_id,
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_ANALYSIS],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_ANALYSIS)

        self._mos_phase = "REPORT_GENERATION"
        await workflow.execute_activity(
            activities.mos_activity_generate_report,
            mos_input.study_id,
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_REPORT],
        )
        await self._mos_wait_transition(E_TRANSITION_AFTER_REPORT)

        await self._mos_wait_transition(E_TRANSITION_BEFORE_ARCHIVE)
        self._mos_phase = "ARCHIVED"
        await workflow.execute_activity(
            activities.mos_activity_archive,
            mos_input.study_id,
            start_to_close_timeout=mos_to[activities.E_ACTIVITY_ARCHIVE],
        )
        return "COMPLETED"

    async def _mos_wait_transition(self, mos_transition_id: str) -> None:
        """Block until signature signal received for transition."""
        await workflow.wait_condition(lambda: self._mos_signed.get(mos_transition_id, False))
