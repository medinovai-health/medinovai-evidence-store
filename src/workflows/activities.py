"""Study lifecycle activities (stubs with structured logs)."""

from __future__ import annotations

from datetime import timedelta

import structlog
from temporalio import activity

mos_logger = structlog.get_logger()

E_ACTIVITY_CREATE = "create_study"
E_ACTIVITY_PROTOCOL = "record_protocol_approval"
E_ACTIVITY_DATA = "collect_study_data"
E_ACTIVITY_ANALYSIS = "run_analysis"
E_ACTIVITY_REPORT = "generate_report"
E_ACTIVITY_ARCHIVE = "archive_study"


@activity.defn(name=E_ACTIVITY_CREATE)
async def mos_activity_create_study(mos_study_id: str) -> str:
    """Initialize study shell record."""
    mos_logger.info("activity_create_study", study_id=mos_study_id, phi_safe=True)
    return f"created:{mos_study_id}"


@activity.defn(name=E_ACTIVITY_PROTOCOL)
async def mos_activity_record_protocol(mos_study_id: str) -> str:
    """Record protocol approval checkpoint (integrate MSS later)."""
    mos_logger.info("activity_protocol", study_id=mos_study_id, phi_safe=True)
    return f"protocol_ok:{mos_study_id}"


@activity.defn(name=E_ACTIVITY_DATA)
async def mos_activity_collect_data(mos_study_id: str) -> str:
    """Stub data collection phase."""
    activity.heartbeat("collect_progress")
    mos_logger.info("activity_collect", study_id=mos_study_id, phi_safe=True)
    return f"data_ok:{mos_study_id}"


@activity.defn(name=E_ACTIVITY_ANALYSIS)
async def mos_activity_run_analysis(mos_study_id: str) -> str:
    """Stub analysis execution."""
    activity.heartbeat("analysis_progress")
    mos_logger.info("activity_analysis", study_id=mos_study_id, phi_safe=True)
    return f"analysis_ok:{mos_study_id}"


@activity.defn(name=E_ACTIVITY_REPORT)
async def mos_activity_generate_report(mos_study_id: str) -> str:
    """Stub report generation."""
    mos_logger.info("activity_report", study_id=mos_study_id, phi_safe=True)
    return f"report_ok:{mos_study_id}"


@activity.defn(name=E_ACTIVITY_ARCHIVE)
async def mos_activity_archive(mos_study_id: str) -> str:
    """Stub WORM archive."""
    mos_logger.info("activity_archive", study_id=mos_study_id, phi_safe=True)
    return f"archived:{mos_study_id}"


def mos_default_activity_timeouts() -> dict[str, timedelta]:
    """Default start-to-close timeouts per activity name."""
    return {
        E_ACTIVITY_CREATE: timedelta(seconds=30),
        E_ACTIVITY_PROTOCOL: timedelta(seconds=60),
        E_ACTIVITY_DATA: timedelta(seconds=300),
        E_ACTIVITY_ANALYSIS: timedelta(seconds=3600),
        E_ACTIVITY_REPORT: timedelta(seconds=120),
        E_ACTIVITY_ARCHIVE: timedelta(seconds=60),
    }
