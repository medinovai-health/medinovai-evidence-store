"""Pytest hooks — skip DB/Temporal for smoke tests."""

from __future__ import annotations

import os

os.environ.setdefault("MOS_SKIP_DB", "true")
os.environ.setdefault("MOS_SKIP_TEMPORAL", "true")
