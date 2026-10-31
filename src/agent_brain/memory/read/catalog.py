"""In-process MemoryEntry catalog for attaching #37 metadata to #39 records.

The ``MemoryStore`` port returns thin ``MemoryRecord`` values. Slice #11
evaluates enriched ``MemoryEntry`` views without altering the store port.
Backends and fixtures register entries here (or supply an equivalent mapping)
keyed by ``record_id``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from agent_brain.memory.errors import MemoryBoundaryError
from agent_brain.memory.read.models import MemoryEntry
from agent_brain.memory.types import MemoryRecord


class MemoryEntryCatalog:
    """Deterministic record_id → MemoryEntry lookup used by the read service."""

    def __init__(self, entries: Iterable[MemoryEntry] | None = None) -> None:
        self._by_id: dict[str, MemoryEntry] = {}
        for entry in entries or ():
            self.register(entry)

    def register(self, entry: MemoryEntry) -> None:
        if not isinstance(entry, MemoryEntry):
            raise TypeError("entry must be a MemoryEntry")
        self._by_id[entry.record.record_id] = entry

    def get(self, record_id: str) -> MemoryEntry | None:
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("record_id must be a non-blank string")
        return self._by_id.get(record_id.strip())

    def require(self, record: MemoryRecord) -> MemoryEntry:
        """Resolve catalog metadata for a recalled record.

        Missing catalog metadata is a hard failure for load-bearing evaluation
        and is surfaced by the service as UNKNOWN / not admissible — callers
        should prefer ``get`` + explicit handling when probing.
        """
        if not isinstance(record, MemoryRecord):
            raise TypeError("record must be a MemoryRecord")
        entry = self._by_id.get(record.record_id)
        if entry is None:
            raise MemoryBoundaryError(
                f"no MemoryEntry metadata registered for record_id={record.record_id!r}"
            )
        if entry.record.record_id != record.record_id:
            raise MemoryBoundaryError("catalog entry record_id mismatch")
        if not entry.record.scope.matches(record.scope):
            raise MemoryBoundaryError(
                "catalog entry scope does not match recalled record scope"
            )
        return entry

    def as_mapping(self) -> Mapping[str, MemoryEntry]:
        return dict(self._by_id)


def entry_from_parts(
    record: MemoryRecord,
    *,
    temporal,
    provenance,
    resolution_meta,
    ttl_seconds: int | None = None,
    live_claim=None,
    session_id: str | None = None,
    schema_version: str = "memory-entry/v1",
) -> MemoryEntry:
    """Helper to build a MemoryEntry without repeating imports in tests."""
    return MemoryEntry(
        schema_version=schema_version,
        record=record,
        temporal=temporal,
        provenance=provenance,
        resolution_meta=resolution_meta,
        ttl_seconds=ttl_seconds,
        live_claim=live_claim,
        session_id=session_id,
    )


__all__ = [
    "MemoryEntryCatalog",
    "entry_from_parts",
]
