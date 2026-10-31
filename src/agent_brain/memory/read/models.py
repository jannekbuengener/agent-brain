"""Read-side Memory models for Slice #11.

Consumes #39 ``MemoryRecord`` / ``MemoryScope`` and #37 temporal / provenance /
resolution contracts without redefining them. ResolutionState is always derived
on the read path — never treated as stored truth.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from agent_brain.contracts.provenance import PROVENANCE_SCHEMA, Provenance
from agent_brain.contracts.resolution import (
    RESOLUTION_META_SCHEMA,
    ResolutionMeta,
    ResolutionState,
)
from agent_brain.contracts.temporal import TEMPORAL_ENVELOPE_SCHEMA, TemporalEnvelope
from agent_brain.contracts.versioning import require_compatible_version
from agent_brain.memory.errors import MemoryBoundaryError
from agent_brain.memory.types import (
    MEMORY_RECORD_SCHEMA,
    MemoryRecord,
    StoreAvailability,
)

MEMORY_ENTRY_SCHEMA = "memory-entry/v1"
MEMORY_READ_ITEM_SCHEMA = "memory-read-item/v1"
MEMORY_READ_RESULT_SCHEMA = "memory-read-result/v1"
LIVE_CLAIM_SCHEMA = "memory-live-claim/v1"
LIVE_REVALIDATION_SCHEMA = "memory-live-revalidation/v1"


class ArtifactKind(StrEnum):
    """Distinguishes Memory rediscovery state from Knowledge-Build state."""

    MEMORY = "memory"
    KNOWLEDGE_BUILD = "knowledge_build"


class LiveRevalidationStatus(StrEnum):
    """Outcome of comparing a Memory claim against higher-authority live state."""

    CONFIRMED = "confirmed"
    CONTRADICTED = "contradicted"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


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


def _optional_non_negative_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(item, field_name) for item in values)


@dataclass(frozen=True, slots=True)
class LiveStateClaim:
    """Optional live-checkable assertion attached to a Memory entry.

    Example: claim_key=\"issue:11:state\", asserted_value=\"open\".
    When present, recall must revalidate against current live state when a
    checker is available. Live authority always outranks Memory.
    """

    schema_version: str
    claim_key: str
    asserted_value: str
    requires_revalidation: bool = True

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="memory-live-claim",
            supported_major=1,
        )
        object.__setattr__(self, "claim_key", _required_text(self.claim_key, "claim_key"))
        object.__setattr__(
            self, "asserted_value", _required_text(self.asserted_value, "asserted_value")
        )
        if not isinstance(self.requires_revalidation, bool):
            raise TypeError("requires_revalidation must be a bool")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_key": self.claim_key,
            "asserted_value": self.asserted_value,
            "requires_revalidation": self.requires_revalidation,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LiveStateClaim:
        if not isinstance(payload, Mapping):
            raise TypeError("LiveStateClaim payload must be a mapping")
        return cls(
            schema_version=payload.get("schema_version", ""),
            claim_key=payload.get("claim_key", ""),
            asserted_value=payload.get("asserted_value", ""),
            requires_revalidation=bool(payload.get("requires_revalidation", True)),
        )


@dataclass(frozen=True, slots=True)
class LiveRevalidationResult:
    """Evidence from Live-State revalidation; never upgrades Memory over Live."""

    schema_version: str
    status: LiveRevalidationStatus
    observed_value: str | None = None
    observed_source: str | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="memory-live-revalidation",
            supported_major=1,
        )
        if isinstance(self.status, str) and not isinstance(
            self.status, LiveRevalidationStatus
        ):
            object.__setattr__(self, "status", LiveRevalidationStatus(self.status))
        if not isinstance(self.status, LiveRevalidationStatus):
            raise TypeError("status must be a LiveRevalidationStatus")
        object.__setattr__(
            self, "observed_value", _optional_text(self.observed_value, "observed_value")
        )
        object.__setattr__(
            self,
            "observed_source",
            _optional_text(self.observed_source, "observed_source"),
        )
        object.__setattr__(
            self, "reason_code", _optional_text(self.reason_code, "reason_code")
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "status": self.status.value,
        }
        if self.observed_value is not None:
            payload["observed_value"] = self.observed_value
        if self.observed_source is not None:
            payload["observed_source"] = self.observed_source
        if self.reason_code is not None:
            payload["reason_code"] = self.reason_code
        return payload


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """MemoryRecord plus required #37 metadata for fail-closed read evaluation.

    ``ttl_seconds`` is an optional freshness window measured from
    ``temporal.known_at``. ``valid_until`` on the TemporalEnvelope remains the
    authoritative validity bound when present (#37).
    """

    schema_version: str
    record: MemoryRecord
    temporal: TemporalEnvelope
    provenance: Provenance
    resolution_meta: ResolutionMeta
    ttl_seconds: int | None = None
    live_claim: LiveStateClaim | None = None
    session_id: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="memory-entry",
            supported_major=1,
        )
        if not isinstance(self.record, MemoryRecord):
            raise TypeError("record must be a MemoryRecord")
        if not isinstance(self.temporal, TemporalEnvelope):
            raise TypeError("temporal must be a TemporalEnvelope")
        if not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be a Provenance")
        if not isinstance(self.resolution_meta, ResolutionMeta):
            raise TypeError("resolution_meta must be a ResolutionMeta")
        object.__setattr__(
            self, "ttl_seconds", _optional_non_negative_int(self.ttl_seconds, "ttl_seconds")
        )
        if self.live_claim is not None and not isinstance(self.live_claim, LiveStateClaim):
            raise TypeError("live_claim must be a LiveStateClaim")
        object.__setattr__(
            self, "session_id", _optional_text(self.session_id, "session_id")
        )
        # known_at on the store record and temporal envelope must agree.
        if self.record.known_at != self.temporal.known_at:
            raise MemoryBoundaryError(
                "record.known_at must match temporal.known_at"
            )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "record": {
                "schema_version": self.record.schema_version,
                "record_id": self.record.record_id,
                "subject_ref": self.record.subject_ref,
                "scope": self.record.scope.to_dict(),
                "content_ref": self.record.content_ref,
                "known_at": self.record.known_at.isoformat() + "Z",
                "summary": self.record.summary,
                "evidence_refs": list(self.record.evidence_refs),
            },
            "temporal": self.temporal.to_dict(),
            "provenance": self.provenance.to_dict(),
            "resolution_meta": self.resolution_meta.to_dict(),
        }
        if self.ttl_seconds is not None:
            payload["ttl_seconds"] = self.ttl_seconds
        if self.live_claim is not None:
            payload["live_claim"] = self.live_claim.to_dict()
        if self.session_id is not None:
            payload["session_id"] = self.session_id
        return payload


@dataclass(frozen=True, slots=True)
class MemoryReadItem:
    """Evaluated Memory entry ready for consumer inspection.

    ``admissible_as_context`` is True only when the derived state is CURRENT and
    live revalidation did not contradict or leave a required check unresolved.
    STALE / SUPERSEDED / UNKNOWN are returned for inspection but must not be
    treated as load-bearing current context.
    """

    schema_version: str
    entry: MemoryEntry
    resolution_state: ResolutionState
    reason_codes: tuple[str, ...]
    admissible_as_context: bool
    artifact_kind: ArtifactKind = ArtifactKind.MEMORY
    live_revalidation: LiveRevalidationResult | None = None
    explanation: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="memory-read-item",
            supported_major=1,
        )
        if not isinstance(self.entry, MemoryEntry):
            raise TypeError("entry must be a MemoryEntry")
        if isinstance(self.resolution_state, str) and not isinstance(
            self.resolution_state, ResolutionState
        ):
            object.__setattr__(
                self, "resolution_state", ResolutionState(self.resolution_state)
            )
        if not isinstance(self.resolution_state, ResolutionState):
            raise TypeError("resolution_state must be a ResolutionState")
        object.__setattr__(
            self, "reason_codes", _text_tuple(self.reason_codes, "reason_codes")
        )
        if not isinstance(self.admissible_as_context, bool):
            raise TypeError("admissible_as_context must be a bool")
        if isinstance(self.artifact_kind, str) and not isinstance(
            self.artifact_kind, ArtifactKind
        ):
            object.__setattr__(self, "artifact_kind", ArtifactKind(self.artifact_kind))
        if not isinstance(self.artifact_kind, ArtifactKind):
            raise TypeError("artifact_kind must be an ArtifactKind")
        if self.artifact_kind is not ArtifactKind.MEMORY:
            raise MemoryBoundaryError(
                "Memory read items must use ArtifactKind.MEMORY"
            )
        if self.live_revalidation is not None and not isinstance(
            self.live_revalidation, LiveRevalidationResult
        ):
            raise TypeError("live_revalidation must be a LiveRevalidationResult")
        object.__setattr__(
            self, "explanation", _optional_text(self.explanation, "explanation")
        )
        if self.admissible_as_context and self.resolution_state is not ResolutionState.CURRENT:
            raise MemoryBoundaryError(
                "only CURRENT items may be admissible_as_context"
            )

    @property
    def is_load_bearing(self) -> bool:
        return self.admissible_as_context


@dataclass(frozen=True, slots=True)
class MemoryReadResult:
    """Outcome of a scoped Memory recall evaluation."""

    schema_version: str
    availability: StoreAvailability
    items: tuple[MemoryReadItem, ...] = ()
    detail: str | None = None
    limitations: tuple[str, ...] = ()
    as_of: datetime | None = None
    artifact_kind: ArtifactKind = ArtifactKind.MEMORY

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="memory-read-result",
            supported_major=1,
        )
        if isinstance(self.availability, str) and not isinstance(
            self.availability, StoreAvailability
        ):
            object.__setattr__(
                self, "availability", StoreAvailability(self.availability)
            )
        if not isinstance(self.availability, StoreAvailability):
            raise TypeError("availability must be a StoreAvailability")
        if not isinstance(self.items, Sequence) or isinstance(self.items, (str, bytes)):
            raise TypeError("items must be a sequence of MemoryReadItem")
        for item in self.items:
            if not isinstance(item, MemoryReadItem):
                raise TypeError("items must contain only MemoryReadItem values")
        object.__setattr__(self, "items", tuple(self.items))
        object.__setattr__(self, "detail", _optional_text(self.detail, "detail"))
        object.__setattr__(
            self, "limitations", _text_tuple(self.limitations, "limitations")
        )
        if isinstance(self.artifact_kind, str) and not isinstance(
            self.artifact_kind, ArtifactKind
        ):
            object.__setattr__(self, "artifact_kind", ArtifactKind(self.artifact_kind))
        if self.artifact_kind is not ArtifactKind.MEMORY:
            raise MemoryBoundaryError(
                "MemoryReadResult must use ArtifactKind.MEMORY"
            )
        if (
            self.availability is StoreAvailability.UNAVAILABLE
            and self.items
        ):
            raise MemoryBoundaryError(
                "unavailable memory read results must not carry items"
            )

    @property
    def admissible_items(self) -> tuple[MemoryReadItem, ...]:
        return tuple(item for item in self.items if item.admissible_as_context)

    @property
    def is_unavailable(self) -> bool:
        return self.availability is StoreAvailability.UNAVAILABLE


# Convenience alias used by docs/tests.
ARTIFACT_KIND_MEMORY = ArtifactKind.MEMORY

__all__ = [
    "ARTIFACT_KIND_MEMORY",
    "LIVE_CLAIM_SCHEMA",
    "LIVE_REVALIDATION_SCHEMA",
    "MEMORY_ENTRY_SCHEMA",
    "MEMORY_READ_ITEM_SCHEMA",
    "MEMORY_READ_RESULT_SCHEMA",
    "MEMORY_RECORD_SCHEMA",
    "PROVENANCE_SCHEMA",
    "RESOLUTION_META_SCHEMA",
    "TEMPORAL_ENVELOPE_SCHEMA",
    "ArtifactKind",
    "LiveRevalidationResult",
    "LiveRevalidationStatus",
    "LiveStateClaim",
    "MemoryEntry",
    "MemoryReadItem",
    "MemoryReadResult",
]
