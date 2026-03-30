"""Temporal worker entrypoint — register workflows and activities."""

from __future__ import annotations

import asyncio
import os

import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from src.settings import mos_get_settings
from src.workflows import activities, sigure_tasks
from src.workflows.study_lifecycle import MosStudyLifecycleWorkflow

mos_logger = structlog.get_logger()


async def mos_run_worker() -> None:
    """Connect and poll task queue."""
    mos_settings = mos_get_settings()
    mos_client = await Client.connect(
        mos_settings.temporal_address,
        namespace=mos_settings.temporal_namespace,
    )
    mos_worker = Worker(
        mos_client,
        task_queue=mos_settings.task_queue,
        workflows=[MosStudyLifecycleWorkflow],
        activities=[
            activities.mos_activity_create_study,
            activities.mos_activity_record_protocol,
            activities.mos_activity_collect_data,
            activities.mos_activity_run_analysis,
            activities.mos_activity_generate_report,
            activities.mos_activity_archive,
            sigure_tasks.mos_activity_verify_electronic_signature,
        ],
    )
    mos_logger.info(
        "worker_start",
        task_queue=mos_settings.task_queue,
        phi_safe=True,
    )
    await mos_worker.run()


def main() -> None:
    """CLI entry."""
    asyncio.run(mos_run_worker())


if __name__ == "__main__":
    if os.getenv("MOS_SKIP_TEMPORAL", "").lower() in ("1", "true", "yes"):
        mos_logger.warning("worker_skip_temporal", phi_safe=True)
    else:
        main()
