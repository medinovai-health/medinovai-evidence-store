"""FastAPI application entry."""

from __future__ import annotations

from fastapi import FastAPI

from src.api.routes import artifacts, audit, health, signatures, studies

app = FastAPI(
    title="medinovai-evidence-store",
    version="0.1.0",
    description="Phase F Tier 1 — study lifecycle, artifacts, Part 11 hooks",
)

app.include_router(health.router)
app.include_router(studies.router)
app.include_router(artifacts.router)
app.include_router(signatures.router)
app.include_router(audit.router)
