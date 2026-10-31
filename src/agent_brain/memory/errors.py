"""Fail-closed errors for memory/knowledge store boundaries (#39)."""

from __future__ import annotations


class MemoryBoundaryError(ValueError):
    """Base error for store/scope boundary violations."""


class InvalidMemoryScope(MemoryBoundaryError):
    """Raised when a MemoryScope is missing, malformed, or inconsistent."""


class StoreUnavailableError(MemoryBoundaryError):
    """Raised when a store backend is explicitly unavailable.

    This is distinct from an empty result set and from an absent record.
    """
