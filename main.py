"""Application entry: FastAPI lifespan wires async PostgreSQL pool and Temporal client."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from temporalio.client import Client
from temporalio.exceptions import TemporalError

from src.api.routes import artifacts, audit, health, signatures, studies
from src.db.connection import mos_close_db, mos_create_schema, mos_init_db
from src.settings import mos_get_settings

mos_logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(mos_app: FastAPI) -> AsyncIterator[None]:
    """Initialize DB pool / schema and optional Temporal client."""
    mos_settings = mos_get_settings()
    mos_app.state.mos_temporal_client = None
    if not mos_settings.skip_db:
        await mos_init_db(mos_settings.database_url)
        await mos_create_schema()
        mos_logger.info("db_pool_ready", phi_safe=True)
    if os.getenv("MOS_SKIP_TEMPORAL", "").lower() not in ("1", "true", "yes"):
        try:
            mos_client = await Client.connect(
                mos_settings.temporal_address,
                namespace=mos_settings.temporal_namespace,
            )
            mos_app.state.mos_temporal_client = mos_client
            mos_logger.info("temporal_client_ready", phi_safe=True)
        except (TemporalError, OSError, RuntimeError) as mos_exc:
            mos_logger.warning(
                "temporal_client_failed",
                error=str(mos_exc),
                phi_safe=True,
            )
    yield
    mos_tc = getattr(mos_app.state, "mos_temporal_client", None)
    if mos_tc is not None:
        try:
            await mos_tc.close()
        except (AttributeError, RuntimeError):
            pass
    if not mos_settings.skip_db:
        await mos_close_db()


app = FastAPI(
    title="medinovai-evidence-store",
    version="0.2.0",
    description="Study lifecycle, PostgreSQL persistence, Temporal orchestration, Part 11 hooks",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(studies.router)
app.include_router(artifacts.router)
app.include_router(signatures.router)
app.include_router(audit.router)


def mos_create_app() -> FastAPI:
    """Factory hook for tests / ASGI servers."""
    return app
