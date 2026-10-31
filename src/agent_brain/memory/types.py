"""Shared store availability and memory read value types (#39).

Availability semantics:
- UNAVAILABLE: backend cannot answer; must not be interpreted as empty/absent
- EMPTY: backend available, query succeeded, zero matching records
- ABSENT: backend available, a concrete ref was looked up and not found
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from agent_brain.contracts.versioning import require_compatible_version
from agent_brain.knowledge.snapshot import KnowledgeSnapshot
from agent_brain.memory.errors import InvalidMemoryScope, MemoryBoundaryError
from agent_brain.memory.scope import MEMORY_SCOPE_SCHEMA, MemoryScope

MEMORY_RECORD_SCHEMA = "memory-record/v1"
MEMORY_RECALL_QUERY_SCHEMA = "memory-recall-query/v1"
MEMORY_RECALL_RESULT_SCHEMA = "memory-recall-result/v1"
STORE_HEALTH_SCHEMA = "store-health/v1"
KNOWLEDGE_QUERY_SCHEMA = "knowledge-query/v1"
KNOWLEDGE_RESULT_SCHEMA = "knowledge-result/v1"
KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA = "knowledge-snapshot-lookup/v1"


class StoreAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class LookupStatus(StrEnum):
    """Status for single-ref lookups.

    OK means the backend answered and the ref was present.
    ABSENT means the backend answered and the ref was not found.
    UNAVAILABLE means the backend could not answer.
    """

    OK = "ok"
    ABSENT = "absent"
    UNAVAILABLE = "unavailable"


class ResultCardinality(StrEnum):
    """Cardinality annotation for multi-record query results when available."""

    NONEMPTY = "nonempty"
    EMPTY = "empty"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _normalize_utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _optional_utc_datetime(value: object, field_name: str) -> datetime | None:
    if value is None:
        return None
    return _normalize_utc_datetime(value, field_name)


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(item, field_name) for item in values)


@dataclass(frozen=True, slots=True)
class StoreHealth:
    """Backend health without leaking concrete backend types."""

    schema_version: str
    availability: StoreAvailability
    detail: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="store-health",
            supported_major=1,
        )
        if isinstance(self.availability, str) and not isinstance(
            self.availability, StoreAvailability
        ):
            object.__setattr__(
                self,
                "availability",
                StoreAvailability(self.availability),
            )
        if not isinstance(self.availability, StoreAvailability):
            raise TypeError("availability must be a StoreAvailability")
        object.__setattr__(self, "detail", _optional_text(self.detail, "detail"))

    @property
    def is_available(self) -> bool:
        return self.availability is StoreAvailability.AVAILABLE

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "availability": self.availability.value,
        }
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    """Backend-neutral episodic/historical memory record for read paths."""

    schema_version: str
    record_id: str
    subject_ref: str
    scope: MemoryScope
    content_ref: str
    known_at: datetime
    summary: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="memory-record",
            supported_major=1,
        )
        object.__setattr__(self, "record_id", _required_text(self.record_id, "record_id"))
        object.__setattr__(
            self, "subject_ref", _required_text(self.subject_ref, "subject_ref")
        )
        if not isinstance(self.scope, MemoryScope):
            raise TypeError("scope must be a MemoryScope")
        object.__setattr__(
            self, "content_ref", _required_text(self.content_ref, "content_ref")
        )
        object.__setattr__(
            self, "known_at", _normalize_utc_datetime(self.known_at, "known_at")
        )
        object.__setattr__(self, "summary", _optional_text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_refs",
            _text_tuple(self.evidence_refs, "evidence_refs"),
        )


@dataclass(frozen=True, slots=True)
class MemoryRecallQuery:
    """Read query that always carries an explicit, validated MemoryScope.

    There is no optional/missing scope. Callers that want an unrestricted
    region must pass an explicit global MemoryScope.
    """

    schema_version: str
    query_id: str
    scope: MemoryScope
    subject_ref: str | None = None
    limit: int = 20
    known_as_of: datetime | None = None
    text_query: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="memory-recall-query",
            supported_major=1,
        )
        object.__setattr__(self, "query_id", _required_text(self.query_id, "query_id"))
        if self.scope is None:
            raise InvalidMemoryScope(
                "scope is required; missing scope is not treated as global"
            )
        if not isinstance(self.scope, MemoryScope):
            raise InvalidMemoryScope("scope must be a MemoryScope")
        # Re-validate to keep fail-closed even if a partially constructed object
        # somehow reached this boundary.
        MemoryScope.from_dict(self.scope.to_dict())
        object.__setattr__(
            self, "subject_ref", _optional_text(self.subject_ref, "subject_ref")
        )
        if isinstance(self.limit, bool) or not isinstance(self.limit, int):
            raise TypeError("limit must be an integer")
        if not 1 <= self.limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000")
        object.__setattr__(
            self, "known_as_of", _optional_utc_datetime(self.known_as_of, "known_as_of")
        )
        object.__setattr__(
            self, "text_query", _optional_text(self.text_query, "text_query")
        )


@dataclass(frozen=True, slots=True)
class MemoryRecallResult:
    """Recall outcome with explicit availability and cardinality."""

    schema_version: str
    availability: StoreAvailability
    records: tuple[MemoryRecord, ...] = ()
    detail: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="memory-recall-result",
            supported_major=1,
        )
        if isinstance(self.availability, str) and not isinstance(
            self.availability, StoreAvailability
        ):
            object.__setattr__(
                self,
                "availability",
                StoreAvailability(self.availability),
            )
        if not isinstance(self.availability, StoreAvailability):
            raise TypeError("availability must be a StoreAvailability")
        if not isinstance(self.records, Sequence) or isinstance(
            self.records, (str, bytes)
        ):
            raise TypeError("records must be a sequence of MemoryRecord")
        for record in self.records:
            if not isinstance(record, MemoryRecord):
                raise TypeError("records must contain only MemoryRecord values")
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "detail", _optional_text(self.detail, "detail"))
        if (
            self.availability is StoreAvailability.UNAVAILABLE
            and self.records
        ):
            raise MemoryBoundaryError(
                "unavailable recall results must not carry records"
            )

    @property
    def cardinality(self) -> ResultCardinality | None:
        if self.availability is StoreAvailability.UNAVAILABLE:
            return None
        return (
            ResultCardinality.EMPTY
            if not self.records
            else ResultCardinality.NONEMPTY
        )

    @property
    def is_unavailable(self) -> bool:
        return self.availability is StoreAvailability.UNAVAILABLE

    @property
    def is_empty(self) -> bool:
        return self.cardinality is ResultCardinality.EMPTY


@dataclass(frozen=True, slots=True)
class KnowledgeQuery:
    """Backend-neutral knowledge read query."""

    schema_version: str
    query_id: str
    text_query: str
    limit: int = 20
    record_type_filter: tuple[str, ...] = ()
    snapshot_ref: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="knowledge-query",
            supported_major=1,
        )
        object.__setattr__(self, "query_id", _required_text(self.query_id, "query_id"))
        object.__setattr__(
            self, "text_query", _required_text(self.text_query, "text_query")
        )
        if isinstance(self.limit, bool) or not isinstance(self.limit, int):
            raise TypeError("limit must be an integer")
        if not 1 <= self.limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000")
        object.__setattr__(
            self,
            "record_type_filter",
            _text_tuple(self.record_type_filter, "record_type_filter"),
        )
        object.__setattr__(
            self, "snapshot_ref", _optional_text(self.snapshot_ref, "snapshot_ref")
        )


@dataclass(frozen=True, slots=True)
class KnowledgeHit:
    """One knowledge hit without backend-specific payload types."""

    record_id: str
    record_type: str
    content_ref: str
    score: float = 0.0
    summary: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _required_text(self.record_id, "record_id"))
        object.__setattr__(
            self, "record_type", _required_text(self.record_type, "record_type")
        )
        object.__setattr__(
            self, "content_ref", _required_text(self.content_ref, "content_ref")
        )
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise TypeError("score must be a number")
        score = float(self.score)
        if not 0.0 <= score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "summary", _optional_text(self.summary, "summary"))


@dataclass(frozen=True, slots=True)
class KnowledgeResult:
    """Knowledge query outcome with explicit availability/cardinality."""

    schema_version: str
    availability: StoreAvailability
    hits: tuple[KnowledgeHit, ...] = ()
    detail: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="knowledge-result",
            supported_major=1,
        )
        if isinstance(self.availability, str) and not isinstance(
            self.availability, StoreAvailability
        ):
            object.__setattr__(
                self,
                "availability",
                StoreAvailability(self.availability),
            )
        if not isinstance(self.availability, StoreAvailability):
            raise TypeError("availability must be a StoreAvailability")
        if not isinstance(self.hits, Sequence) or isinstance(self.hits, (str, bytes)):
            raise TypeError("hits must be a sequence of KnowledgeHit")
        for hit in self.hits:
            if not isinstance(hit, KnowledgeHit):
                raise TypeError("hits must contain only KnowledgeHit values")
        object.__setattr__(self, "hits", tuple(self.hits))
        object.__setattr__(self, "detail", _optional_text(self.detail, "detail"))
        if self.availability is StoreAvailability.UNAVAILABLE and self.hits:
            raise MemoryBoundaryError("unavailable knowledge results must not carry hits")

    @property
    def cardinality(self) -> ResultCardinality | None:
        if self.availability is StoreAvailability.UNAVAILABLE:
            return None
        return ResultCardinality.EMPTY if not self.hits else ResultCardinality.NONEMPTY

    @property
    def is_unavailable(self) -> bool:
        return self.availability is StoreAvailability.UNAVAILABLE

    @property
    def is_empty(self) -> bool:
        return self.cardinality is ResultCardinality.EMPTY


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshotLookup:
    """Single-ref snapshot lookup distinguishing OK / ABSENT / UNAVAILABLE."""

    schema_version: str
    status: LookupStatus
    snapshot_ref: str
    snapshot: KnowledgeSnapshot | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="knowledge-snapshot-lookup",
            supported_major=1,
        )
        if isinstance(self.status, str) and not isinstance(self.status, LookupStatus):
            object.__setattr__(self, "status", LookupStatus(self.status))
        if not isinstance(self.status, LookupStatus):
            raise TypeError("status must be a LookupStatus")
        object.__setattr__(
            self, "snapshot_ref", _required_text(self.snapshot_ref, "snapshot_ref")
        )
        object.__setattr__(self, "detail", _optional_text(self.detail, "detail"))
        if self.status is LookupStatus.OK:
            if self.snapshot is None:
                raise MemoryBoundaryError("OK snapshot lookup requires a snapshot")
            if not isinstance(self.snapshot, KnowledgeSnapshot):
                raise TypeError("snapshot must be a KnowledgeSnapshot")
        if self.status is not LookupStatus.OK and self.snapshot is not None:
            raise MemoryBoundaryError(
                "ABSENT/UNAVAILABLE snapshot lookup must not carry a snapshot"
            )


def require_memory_scope(scope: object) -> MemoryScope:
    """Fail-closed helper used by ports/adapters."""
    if scope is None:
        raise InvalidMemoryScope(
            "scope is required; missing scope is not treated as global"
        )
    if isinstance(scope, MemoryScope):
        # Re-run validation through round-trip to catch tampering.
        return MemoryScope.from_dict(scope.to_dict())
    if isinstance(scope, Mapping):
        return MemoryScope.from_dict(scope)
    raise InvalidMemoryScope("scope must be a MemoryScope")


def default_store_health(availability: StoreAvailability, detail: str | None = None) -> StoreHealth:
    return StoreHealth(
        schema_version=STORE_HEALTH_SCHEMA,
        availability=availability,
        detail=detail,
    )


__all__ = [
    "KNOWLEDGE_QUERY_SCHEMA",
    "KNOWLEDGE_RESULT_SCHEMA",
    "KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA",
    "MEMORY_RECALL_QUERY_SCHEMA",
    "MEMORY_RECALL_RESULT_SCHEMA",
    "MEMORY_RECORD_SCHEMA",
    "MEMORY_SCOPE_SCHEMA",
    "STORE_HEALTH_SCHEMA",
    "KnowledgeHit",
    "KnowledgeQuery",
    "KnowledgeResult",
    "KnowledgeSnapshotLookup",
    "LookupStatus",
    "MemoryRecallQuery",
    "MemoryRecallResult",
    "MemoryRecord",
    "ResultCardinality",
    "StoreAvailability",
    "StoreHealth",
    "default_store_health",
    "require_memory_scope",
]
