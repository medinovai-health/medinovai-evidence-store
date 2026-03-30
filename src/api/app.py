"""Compatibility import: canonical app lives in repo-root `main.py`."""

from __future__ import annotations

from main import app

__all__ = ["app"]
