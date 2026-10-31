"""Fixture / in-memory KnowledgeStore and MemoryStore adapters (#39).

These adapters let consumers test against the #39 ports without SurrealDB.
Scope isolation is exact: records are only visible under the MemoryScope they
were stored with — no hierarchical fallback.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from agent_brain.knowledge.snapshot import KnowledgeSnapshot
from agent_brain.memory.errors import InvalidMemoryScope
from agent_brain.memory.scope import MemoryScope
from agent_brain.memory.types import (
    KNOWLEDGE_RESULT_SCHEMA,
    KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
    MEMORY_RECALL_RESULT_SCHEMA,
    STORE_HEALTH_SCHEMA,
    KnowledgeHit,
    KnowledgeQuery,
    KnowledgeResult,
    KnowledgeSnapshotLookup,
    LookupStatus,
    MemoryRecallQuery,
    MemoryRecallResult,
    MemoryRecord,
    StoreAvailability,
    StoreHealth,
    require_memory_scope,
)


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    from datetime import UTC

    return value.astimezone(UTC).replace(tzinfo=None)


class InMemoryKnowledgeStore:
    """Deterministic fixture KnowledgeStore for unit/contract tests."""

    def __init__(
        self,
        *,
        hits: Iterable[KnowledgeHit] | None = None,
        snapshots: dict[str, KnowledgeSnapshot] | None = None,
        available: bool = True,
    ) -> None:
        self._hits = tuple(hits or ())
        self._snapshots = dict(snapshots or {})
        self._available = available

    def mark_unavailable(self) -> None:
        self._available = False

    def mark_available(self) -> None:
        self._available = True

    async def query(self, query: KnowledgeQuery) -> KnowledgeResult:
        if not isinstance(query, KnowledgeQuery):
            raise TypeError("query must be a KnowledgeQuery")
        if not self._available:
            return KnowledgeResult(
                schema_version=KNOWLEDGE_RESULT_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                hits=(),
                detail="knowledge store unavailable",
            )
        selected: list[KnowledgeHit] = []
        needle = query.text_query.casefold()
        for hit in self._hits:
            if query.record_type_filter and hit.record_type not in query.record_type_filter:
                continue
            haystack = " ".join(
                part for part in (hit.record_id, hit.content_ref, hit.summary or "") if part
            ).casefold()
            if needle not in haystack and needle not in hit.record_type.casefold():
                continue
            selected.append(hit)
            if len(selected) >= query.limit:
                break
        return KnowledgeResult(
            schema_version=KNOWLEDGE_RESULT_SCHEMA,
            availability=StoreAvailability.AVAILABLE,
            hits=tuple(selected),
        )

    async def get_snapshot(self, snapshot_ref: str) -> KnowledgeSnapshotLookup:
        if not isinstance(snapshot_ref, str) or not snapshot_ref.strip():
            raise ValueError("snapshot_ref must be a non-blank string")
        ref = snapshot_ref.strip()
        if not self._available:
            return KnowledgeSnapshotLookup(
                schema_version=KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
                status=LookupStatus.UNAVAILABLE,
                snapshot_ref=ref,
                detail="knowledge store unavailable",
            )
        snapshot = self._snapshots.get(ref)
        if snapshot is None:
            return KnowledgeSnapshotLookup(
                schema_version=KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
                status=LookupStatus.ABSENT,
                snapshot_ref=ref,
            )
        return KnowledgeSnapshotLookup(
            schema_version=KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
            status=LookupStatus.OK,
            snapshot_ref=ref,
            snapshot=snapshot,
        )

    async def health(self) -> StoreHealth:
        return StoreHealth(
            schema_version=STORE_HEALTH_SCHEMA,
            availability=(
                StoreAvailability.AVAILABLE
                if self._available
                else StoreAvailability.UNAVAILABLE
            ),
            detail=None if self._available else "knowledge store unavailable",
        )


class InMemoryMemoryStore:
    """Deterministic fixture MemoryStore with exact scope isolation."""

    def __init__(
        self,
        *,
        records: Iterable[MemoryRecord] | None = None,
        available: bool = True,
    ) -> None:
        self._records = tuple(records or ())
        self._available = available

    def mark_unavailable(self) -> None:
        self._available = False

    def mark_available(self) -> None:
        self._available = True

    def _scoped(
        self,
        scope: MemoryScope,
        *,
        subject_ref: str | None = None,
        known_as_of: datetime | None = None,
        limit: int | None = None,
    ) -> tuple[MemoryRecord, ...]:
        validated = require_memory_scope(scope)
        cutoff = _normalize_utc(known_as_of)
        matched: list[MemoryRecord] = []
        for record in sorted(
            self._records,
            key=lambda item: (item.known_at.isoformat(), item.record_id),
        ):
            if not record.scope.matches(validated):
                continue
            if subject_ref is not None and record.subject_ref != subject_ref:
                continue
            if cutoff is not None and record.known_at > cutoff:
                continue
            matched.append(record)
            if limit is not None and len(matched) >= limit:
                break
        return tuple(matched)

    async def recall(self, query: MemoryRecallQuery) -> MemoryRecallResult:
        if not isinstance(query, MemoryRecallQuery):
            raise TypeError("query must be a MemoryRecallQuery")
        # Construction already validates scope; re-check for defense in depth.
        require_memory_scope(query.scope)
        if not self._available:
            return MemoryRecallResult(
                schema_version=MEMORY_RECALL_RESULT_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                records=(),
                detail="memory store unavailable",
            )
        records = self._scoped(
            query.scope,
            subject_ref=query.subject_ref,
            known_as_of=query.known_as_of,
            limit=query.limit,
        )
        if query.text_query:
            needle = query.text_query.casefold()
            records = tuple(
                record
                for record in records
                if needle
                in " ".join(
                    part
                    for part in (record.record_id, record.content_ref, record.summary or "")
                    if part
                ).casefold()
            )
        return MemoryRecallResult(
            schema_version=MEMORY_RECALL_RESULT_SCHEMA,
            availability=StoreAvailability.AVAILABLE,
            records=records,
        )

    async def history(
        self,
        subject_ref: str,
        *,
        scope: MemoryScope,
        known_as_of: datetime | None = None,
    ) -> MemoryRecallResult:
        if not isinstance(subject_ref, str) or not subject_ref.strip():
            raise InvalidMemoryScope("subject_ref must be a non-blank string")
        require_memory_scope(scope)
        if not self._available:
            return MemoryRecallResult(
                schema_version=MEMORY_RECALL_RESULT_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                records=(),
                detail="memory store unavailable",
            )
        records = self._scoped(
            scope,
            subject_ref=subject_ref.strip(),
            known_as_of=known_as_of,
        )
        return MemoryRecallResult(
            schema_version=MEMORY_RECALL_RESULT_SCHEMA,
            availability=StoreAvailability.AVAILABLE,
            records=records,
        )

    async def health(self) -> StoreHealth:
        return StoreHealth(
            schema_version=STORE_HEALTH_SCHEMA,
            availability=(
                StoreAvailability.AVAILABLE
                if self._available
                else StoreAvailability.UNAVAILABLE
            ),
            detail=None if self._available else "memory store unavailable",
        )
