"""Backward-compatible worker entry — delegates to `src.temporal_worker`."""

from __future__ import annotations

from src.temporal_worker import main

if __name__ == "__main__":
    main()
