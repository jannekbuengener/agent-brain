"""Portable run-id helpers extracted from the foundation baseline."""

from __future__ import annotations

import json
from pathlib import Path

from .time import Clock, utcnow


def timestamp_run_id(clock: Clock | None = None) -> str:
    """Return a deterministic-friendly YYYYMMDDHHMMSS run identifier."""
    current = utcnow(clock)
    return (
        f"{current.year:04d}{current.month:02d}{current.day:02d}"
        f"{current.hour:02d}{current.minute:02d}{current.second:02d}"
    )


def run_id_from_snapshot(snapshot_path: str | Path) -> str:
    """Read and stringify the run_id field from a JSON snapshot."""
    data = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    return str(data["run_id"])
