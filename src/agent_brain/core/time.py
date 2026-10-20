"""Injectable UTC clock primitives for deterministic foundation code."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    """Clock interface used by deterministic consumers."""

    def now(self) -> datetime:
        """Return the current time as a naive UTC datetime."""


class SystemClock:
    """System-backed UTC clock preserving the legacy naive datetime shape."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)


class FixedClock:
    """Explicitly controlled clock for tests and deterministic flows."""

    def __init__(self, fixed_time: datetime):
        self._fixed_time = fixed_time

    def now(self) -> datetime:
        return self._fixed_time

    def set_time(self, new_time: datetime) -> None:
        self._fixed_time = new_time


_DEFAULT_CLOCK: Clock = SystemClock()


def set_default_clock(clock: Clock) -> None:
    """Replace the process-local default clock."""
    global _DEFAULT_CLOCK
    _DEFAULT_CLOCK = clock


def get_default_clock() -> Clock:
    """Return the process-local default clock."""
    return _DEFAULT_CLOCK


def utcnow(clock: Clock | None = None) -> datetime:
    """Return UTC time from an injected clock or the process-local default."""
    return (clock or _DEFAULT_CLOCK).now()
