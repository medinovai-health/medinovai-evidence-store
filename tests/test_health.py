"""Smoke tests for public HTTP surface."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import app


def test_health_returns_ok() -> None:
    """GET /health is 200 and marks phi_safe."""
    mos_client = TestClient(app)
    mos_resp = mos_client.get("/health")
    assert mos_resp.status_code == 200
    mos_body = mos_resp.json()
    assert mos_body["status"] == "healthy"
    assert mos_body.get("phi_safe") is True


def test_ready_returns_ok() -> None:
    """GET /ready is 200."""
    mos_client = TestClient(app)
    mos_resp = mos_client.get("/ready")
    assert mos_resp.status_code == 200
