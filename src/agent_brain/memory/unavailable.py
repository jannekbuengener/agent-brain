"""Explicit unavailable KnowledgeStore / MemoryStore adapters (#39).

UNAVAILABLE is never represented as an empty hit/record list alone. Callers
must inspect availability / LookupStatus.
"""

from __future__ import annotations

from datetime import datetime

from agent_brain.memory.scope import MemoryScope
from agent_brain.memory.types import (
    KNOWLEDGE_RESULT_SCHEMA,
    KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
    MEMORY_RECALL_RESULT_SCHEMA,
    STORE_HEALTH_SCHEMA,
    KnowledgeQuery,
    KnowledgeResult,
    KnowledgeSnapshotLookup,
    LookupStatus,
    MemoryRecallQuery,
    MemoryRecallResult,
    StoreAvailability,
    StoreHealth,
    require_memory_scope,
)


class UnavailableKnowledgeStore:
    """Always-unavailable KnowledgeStore for safe degradation tests."""

    def __init__(self, *, detail: str = "knowledge store unavailable") -> None:
        self._detail = detail

    async def query(self, query: KnowledgeQuery) -> KnowledgeResult:
        if not isinstance(query, KnowledgeQuery):
            raise TypeError("query must be a KnowledgeQuery")
        return KnowledgeResult(
            schema_version=KNOWLEDGE_RESULT_SCHEMA,
            availability=StoreAvailability.UNAVAILABLE,
            hits=(),
            detail=self._detail,
        )

    async def get_snapshot(self, snapshot_ref: str) -> KnowledgeSnapshotLookup:
        if not isinstance(snapshot_ref, str) or not snapshot_ref.strip():
            raise ValueError("snapshot_ref must be a non-blank string")
        return KnowledgeSnapshotLookup(
            schema_version=KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
            status=LookupStatus.UNAVAILABLE,
            snapshot_ref=snapshot_ref.strip(),
            detail=self._detail,
        )

    async def health(self) -> StoreHealth:
        return StoreHealth(
            schema_version=STORE_HEALTH_SCHEMA,
            availability=StoreAvailability.UNAVAILABLE,
            detail=self._detail,
        )


class UnavailableMemoryStore:
    """Always-unavailable MemoryStore for safe degradation tests."""

    def __init__(self, *, detail: str = "memory store unavailable") -> None:
        self._detail = detail

    async def recall(self, query: MemoryRecallQuery) -> MemoryRecallResult:
        if not isinstance(query, MemoryRecallQuery):
            raise TypeError("query must be a MemoryRecallQuery")
        require_memory_scope(query.scope)
        return MemoryRecallResult(
            schema_version=MEMORY_RECALL_RESULT_SCHEMA,
            availability=StoreAvailability.UNAVAILABLE,
            records=(),
            detail=self._detail,
        )

    async def history(
        self,
        subject_ref: str,
        *,
        scope: MemoryScope,
        known_as_of: datetime | None = None,
    ) -> MemoryRecallResult:
        del known_as_of  # accepted for signature parity; unused when unavailable
        if not isinstance(subject_ref, str) or not subject_ref.strip():
            raise ValueError("subject_ref must be a non-blank string")
        require_memory_scope(scope)
        return MemoryRecallResult(
            schema_version=MEMORY_RECALL_RESULT_SCHEMA,
            availability=StoreAvailability.UNAVAILABLE,
            records=(),
            detail=self._detail,
        )

    async def health(self) -> StoreHealth:
        return StoreHealth(
            schema_version=STORE_HEALTH_SCHEMA,
            availability=StoreAvailability.UNAVAILABLE,
            detail=self._detail,
        )
