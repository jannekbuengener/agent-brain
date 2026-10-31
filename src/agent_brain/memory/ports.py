"""Backend-neutral read-only KnowledgeStore and MemoryStore ports (#39).

These protocols intentionally exclude write/remember/consolidate surfaces.
Concrete backends (SurrealDB, fixtures, future adapters) implement them
without leaking SDK types into core signatures.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from agent_brain.memory.scope import MemoryScope
from agent_brain.memory.types import (
    KnowledgeQuery,
    KnowledgeResult,
    KnowledgeSnapshotLookup,
    MemoryRecallQuery,
    MemoryRecallResult,
    MemoryRecord,
    StoreHealth,
)

# Methods that must never appear on read-only store ports.
FORBIDDEN_WRITE_METHODS = frozenset(
    {
        "write",
        "remember",
        "reflect",
        "forget",
        "consolidate",
        "delete",
        "upsert",
        "mutate",
    }
)


@runtime_checkable
class KnowledgeStore(Protocol):
    """Read-only knowledge/snapshot port."""

    async def query(self, query: KnowledgeQuery) -> KnowledgeResult:
        """Execute a backend-neutral knowledge query."""

    async def get_snapshot(self, snapshot_ref: str) -> KnowledgeSnapshotLookup:
        """Look up one snapshot; distinguishes OK / ABSENT / UNAVAILABLE."""

    async def health(self) -> StoreHealth:
        """Report backend availability without backend-specific types."""


@runtime_checkable
class MemoryStore(Protocol):
    """Read-only memory recall/history port."""

    async def recall(self, query: MemoryRecallQuery) -> MemoryRecallResult:
        """Recall records for an explicit, validated MemoryScope."""

    async def history(
        self,
        subject_ref: str,
        *,
        scope: MemoryScope,
        known_as_of: datetime | None = None,
    ) -> Sequence[MemoryRecord] | MemoryRecallResult:
        """Return subject history constrained to the given scope.

        Implementations may return either a sequence (when available) or a
        MemoryRecallResult that can express UNAVAILABLE explicitly. Callers
        must treat UNAVAILABLE as distinct from an empty sequence.
        """

    async def health(self) -> StoreHealth:
        """Report backend availability without backend-specific types."""


def assert_read_only_store(store: object) -> None:
    """Fail if a store object exposes forbidden write-like methods."""
    for name in FORBIDDEN_WRITE_METHODS:
        attr = getattr(store, name, None)
        if callable(attr):
            raise TypeError(f"read-only store must not expose {name}()")
