"""Temporal worker: polls task queue with DB-backed activities."""

from __future__ import annotations

import asyncio
import os

import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from src.db.connection import mos_close_db, mos_create_schema, mos_init_db
from src.settings import mos_get_settings
from src.workflows import activities, sigure_tasks
from src.workflows.study_lifecycle import StudyLifecycleWorkflow

mos_logger = structlog.get_logger()


async def mos_run_worker() -> None:
    """Connect to PostgreSQL and Temporal; register workflows and activities."""
    mos_settings = mos_get_settings()
    if not mos_settings.skip_db:
        await mos_init_db(mos_settings.database_url)
        await mos_create_schema()
    mos_client = await Client.connect(
        mos_settings.temporal_address,
        namespace=mos_settings.temporal_namespace,
    )
    mos_worker = Worker(
        mos_client,
        task_queue=mos_settings.task_queue,
        workflows=[StudyLifecycleWorkflow],
        activities=[
            activities.mos_activity_create_study,
            activities.mos_activity_upload_artifact,
            activities.mos_activity_verify_integrity,
            activities.mos_activity_collect_signature,
            activities.mos_activity_archive_study,
            sigure_tasks.mos_activity_verify_electronic_signature,
        ],
    )
    mos_logger.info(
        "temporal_worker_start",
        task_queue=mos_settings.task_queue,
        phi_safe=True,
    )
    try:
        await mos_worker.run()
    finally:
        if not mos_settings.skip_db:
            await mos_close_db()


def main() -> None:
    """CLI entry for `python -m src.temporal_worker`."""
    if os.getenv("MOS_SKIP_TEMPORAL", "").lower() in ("1", "true", "yes"):
        mos_logger.warning("worker_skip_temporal", phi_safe=True)
        return
    asyncio.run(mos_run_worker())


if __name__ == "__main__":
    main()
