"""Backend-neutral Skill Improvement Blackboard contracts (#46).

These types define durable Improvement identity, append-only Observations,
lifecycle transitions, and merge lineage. They do not provide storage,
protocol surfaces, GitHub mutation, or MemoryStore/KnowledgeStore writes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from agent_brain.contracts._validation import (
    format_utc_datetime,
    normalize_utc_datetime,
    optional_text,
    optional_unit_interval,
    parse_optional_utc_datetime,
    parse_utc_datetime,
    required_text,
    text_tuple,
)
from agent_brain.contracts.provenance import Provenance
from agent_brain.contracts.resolution import ResolutionMeta
from agent_brain.contracts.temporal import TemporalEnvelope
from agent_brain.contracts.versioning import require_compatible_version

IMPROVEMENT_SCHEMA = "improvement/v1"
IMPROVEMENT_OBSERVATION_SCHEMA = "improvement-observation/v1"
IMPROVEMENT_MERGE_LINEAGE_SCHEMA = "improvement-merge-lineage/v1"
IMPROVEMENT_WORK_REF_SCHEMA = "improvement-work-ref/v1"

_ROOT_CAUSE_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


class ImprovementLifecycle(StrEnum):
    """Canonical Improvement lifecycle — not Workforce Finding lifecycle."""

    NEW = "NEW"
    RECURRING = "RECURRING"
    VALIDATED = "VALIDATED"
    PLANNED = "PLANNED"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"


class ImprovementPriority(StrEnum):
    """Board-managed priority vocabulary."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DedupeRelationKind(StrEnum):
    """Conservative relation kinds; similarity alone never auto-merges."""

    EXACT_IDENTITY = "EXACT_IDENTITY"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    RELATED = "RELATED"


class WorkRefKind(StrEnum):
    """External execution-truth references owned by GitHub/repo live state."""

    GITHUB_ISSUE = "GITHUB_ISSUE"
    GITHUB_PULL_REQUEST = "GITHUB_PULL_REQUEST"
    VERIFICATION = "VERIFICATION"


# Explicit transition matrix. Ambiguous/unauthorized transitions → HOLD at
# management boundary; this contract only encodes structural legality.
ALLOWED_LIFECYCLE_TRANSITIONS: Mapping[ImprovementLifecycle, frozenset[ImprovementLifecycle]] = {
    ImprovementLifecycle.NEW: frozenset(
        {
            ImprovementLifecycle.RECURRING,
            ImprovementLifecycle.CLOSED,
        }
    ),
    ImprovementLifecycle.RECURRING: frozenset(
        {
            ImprovementLifecycle.VALIDATED,
            ImprovementLifecycle.CLOSED,
        }
    ),
    ImprovementLifecycle.VALIDATED: frozenset(
        {
            ImprovementLifecycle.PLANNED,
            ImprovementLifecycle.CLOSED,
        }
    ),
    ImprovementLifecycle.PLANNED: frozenset(
        {
            ImprovementLifecycle.IMPLEMENTED,
            ImprovementLifecycle.CLOSED,
        }
    ),
    ImprovementLifecycle.IMPLEMENTED: frozenset(
        {
            ImprovementLifecycle.VERIFIED,
            ImprovementLifecycle.CLOSED,
        }
    ),
    ImprovementLifecycle.VERIFIED: frozenset({ImprovementLifecycle.CLOSED}),
    ImprovementLifecycle.CLOSED: frozenset(),
}


def normalize_root_cause_key(value: object, field_name: str = "root_cause_key") -> str:
    """Normalize a root-cause identity slug to lowercase kebab-case.

    Identity is deterministic: wording/synonyms alone do not create a new key.
    Callers that cannot determine a confident key must fail closed upstream
    instead of inventing one.
    """
    text = required_text(value, field_name).lower()
    text = _SLUG_NORMALIZE_RE.sub("-", text).strip("-")
    if not text or not _ROOT_CAUSE_KEY_RE.fullmatch(text):
        raise ValueError(f"{field_name} must be lowercase kebab-case")
    return text


def build_improvement_id(*, skill_id: str, root_cause_key: str) -> str:
    """Build the stable Improvement identity from skill + root-cause scope."""
    skill = required_text(skill_id, "skill_id").lower()
    key = normalize_root_cause_key(root_cause_key)
    return f"improvement:{skill}:{key}"


def derive_recurrence(valid_observation_count: object) -> int:
    """Derive recurrence from valid observation events — never client ++."""
    if isinstance(valid_observation_count, bool) or not isinstance(valid_observation_count, int):
        raise TypeError("valid_observation_count must be an integer")
    if valid_observation_count < 0:
        raise ValueError("valid_observation_count must be >= 0")
    return valid_observation_count


def is_lifecycle_transition_allowed(
    current: ImprovementLifecycle | str,
    target: ImprovementLifecycle | str,
) -> bool:
    """Return whether ``current -> target`` is structurally allowed."""
    current_state = ImprovementLifecycle(current)
    target_state = ImprovementLifecycle(target)
    if current_state == target_state:
        return True
    return target_state in ALLOWED_LIFECYCLE_TRANSITIONS[current_state]


def require_lifecycle_transition(
    current: ImprovementLifecycle | str,
    target: ImprovementLifecycle | str,
) -> None:
    """Raise ValueError when a lifecycle transition is structurally illegal."""
    if not is_lifecycle_transition_allowed(current, target):
        raise ValueError(
            f"illegal lifecycle transition: {ImprovementLifecycle(current).value} -> "
            f"{ImprovementLifecycle(target).value}"
        )


def _optional_enum(value: object, enum_type: type[StrEnum], field_name: str) -> StrEnum | None:
    if value is None:
        return None
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string or {enum_type.__name__}")
    try:
        return enum_type(required_text(value, field_name))
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}: {value!r}") from exc


def _required_enum(value: object, enum_type: type[StrEnum], field_name: str) -> StrEnum:
    resolved = _optional_enum(value, enum_type, field_name)
    if resolved is None:
        raise ValueError(f"{field_name} is required")
    return resolved


@dataclass(frozen=True, slots=True)
class ImprovementWorkRef:
    """Pointer to GitHub/repo execution truth — not a second mutable authority."""

    schema_version: str
    kind: WorkRefKind
    repository_ref: str
    ref: str
    url: str | None = None
    linked_at: datetime | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="improvement-work-ref",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "kind",
            _required_enum(self.kind, WorkRefKind, "kind"),
        )
        object.__setattr__(
            self,
            "repository_ref",
            required_text(self.repository_ref, "repository_ref"),
        )
        object.__setattr__(self, "ref", required_text(self.ref, "ref"))
        object.__setattr__(self, "url", optional_text(self.url, "url"))
        if self.linked_at is not None:
            object.__setattr__(
                self,
                "linked_at",
                normalize_utc_datetime(self.linked_at, "linked_at"),
            )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "kind": self.kind.value,
            "repository_ref": self.repository_ref,
            "ref": self.ref,
        }
        if self.url is not None:
            payload["url"] = self.url
        if self.linked_at is not None:
            payload["linked_at"] = format_utc_datetime(self.linked_at)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ImprovementWorkRef:
        return cls(
            schema_version=payload.get("schema_version", ""),
            kind=payload.get("kind", ""),
            repository_ref=payload.get("repository_ref", ""),
            ref=payload.get("ref", ""),
            url=payload.get("url"),
            linked_at=parse_optional_utc_datetime(payload.get("linked_at"), "linked_at"),
        )


@dataclass(frozen=True, slots=True)
class ImprovementRelation:
    """Conservative relatedness; never implies automatic merge authority."""

    related_improvement_id: str
    kind: DedupeRelationKind
    reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "related_improvement_id",
            required_text(self.related_improvement_id, "related_improvement_id"),
        )
        object.__setattr__(
            self,
            "kind",
            _required_enum(self.kind, DedupeRelationKind, "kind"),
        )
        object.__setattr__(self, "reason", optional_text(self.reason, "reason"))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "related_improvement_id": self.related_improvement_id,
            "kind": self.kind.value,
        }
        if self.reason is not None:
            payload["reason"] = self.reason
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ImprovementRelation:
        return cls(
            related_improvement_id=payload.get("related_improvement_id", ""),
            kind=payload.get("kind", ""),
            reason=payload.get("reason"),
        )


@dataclass(frozen=True, slots=True)
class ImprovementMergeLineage:
    """Audited merge record preserving source identities."""

    schema_version: str
    merge_id: str
    target_improvement_id: str
    source_improvement_ids: tuple[str, ...]
    actor_id: str
    reason: str
    evidence: tuple[str, ...]
    merged_at: datetime
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="improvement-merge-lineage",
            supported_major=1,
        )
        object.__setattr__(self, "merge_id", required_text(self.merge_id, "merge_id"))
        object.__setattr__(
            self,
            "target_improvement_id",
            required_text(self.target_improvement_id, "target_improvement_id"),
        )
        sources = text_tuple(self.source_improvement_ids, "source_improvement_ids")
        if not sources:
            raise ValueError("source_improvement_ids must not be empty")
        if self.target_improvement_id in sources:
            raise ValueError("target_improvement_id must not appear in source_improvement_ids")
        object.__setattr__(self, "source_improvement_ids", sources)
        object.__setattr__(self, "actor_id", required_text(self.actor_id, "actor_id"))
        object.__setattr__(self, "reason", required_text(self.reason, "reason"))
        object.__setattr__(self, "evidence", text_tuple(self.evidence, "evidence"))
        object.__setattr__(
            self,
            "merged_at",
            normalize_utc_datetime(self.merged_at, "merged_at"),
        )
        if self.provenance is not None and not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be a Provenance")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "merge_id": self.merge_id,
            "target_improvement_id": self.target_improvement_id,
            "source_improvement_ids": list(self.source_improvement_ids),
            "actor_id": self.actor_id,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "merged_at": format_utc_datetime(self.merged_at),
        }
        if self.provenance is not None:
            payload["provenance"] = self.provenance.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ImprovementMergeLineage:
        raw_provenance = payload.get("provenance")
        return cls(
            schema_version=payload.get("schema_version", ""),
            merge_id=payload.get("merge_id", ""),
            target_improvement_id=payload.get("target_improvement_id", ""),
            source_improvement_ids=payload.get("source_improvement_ids", ()),
            actor_id=payload.get("actor_id", ""),
            reason=payload.get("reason", ""),
            evidence=payload.get("evidence", ()),
            merged_at=parse_utc_datetime(payload.get("merged_at"), "merged_at"),
            provenance=(
                None
                if raw_provenance is None
                else Provenance.from_dict(raw_provenance)
                if isinstance(raw_provenance, Mapping)
                else raw_provenance
            ),
        )


@dataclass(frozen=True, slots=True)
class Improvement:
    """Stable root-cause Improvement identity with derived recurrence snapshot.

    ``recurrence`` is a derived projection of valid Observation events. Clients
    must not invent independent recurrence counters; stores recompute it from
    append-only observations.
    """

    schema_version: str
    improvement_id: str
    skill_id: str
    root_cause_key: str
    summary: str
    recommendation: str
    expected_benefit: str
    lifecycle: ImprovementLifecycle
    first_seen: datetime
    last_seen: datetime
    skill_version_ref: str | None = None
    confidence: float | None = None
    priority: ImprovementPriority | None = None
    recurrence: int = 0
    repository_refs: tuple[str, ...] = ()
    task_refs: tuple[str, ...] = ()
    related_skill_ids: tuple[str, ...] = ()
    relations: tuple[ImprovementRelation, ...] = ()
    work_refs: tuple[ImprovementWorkRef, ...] = ()
    merge_lineage: tuple[ImprovementMergeLineage, ...] = ()
    revision: int = 1
    temporal: TemporalEnvelope | None = None
    resolution: ResolutionMeta | None = None
    superseded_by_improvement_id: str | None = None
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="improvement",
            supported_major=1,
        )
        skill_id = required_text(self.skill_id, "skill_id")
        root_cause_key = normalize_root_cause_key(self.root_cause_key)
        improvement_id = required_text(self.improvement_id, "improvement_id")
        expected_id = build_improvement_id(skill_id=skill_id, root_cause_key=root_cause_key)
        if improvement_id != expected_id:
            raise ValueError(
                "improvement_id must equal build_improvement_id(skill_id, root_cause_key)"
            )
        object.__setattr__(self, "skill_id", skill_id)
        object.__setattr__(self, "root_cause_key", root_cause_key)
        object.__setattr__(self, "improvement_id", improvement_id)
        object.__setattr__(self, "summary", required_text(self.summary, "summary"))
        object.__setattr__(
            self,
            "recommendation",
            required_text(self.recommendation, "recommendation"),
        )
        object.__setattr__(
            self,
            "expected_benefit",
            required_text(self.expected_benefit, "expected_benefit"),
        )
        object.__setattr__(
            self,
            "lifecycle",
            _required_enum(self.lifecycle, ImprovementLifecycle, "lifecycle"),
        )
        object.__setattr__(
            self,
            "first_seen",
            normalize_utc_datetime(self.first_seen, "first_seen"),
        )
        object.__setattr__(
            self,
            "last_seen",
            normalize_utc_datetime(self.last_seen, "last_seen"),
        )
        if self.last_seen < self.first_seen:
            raise ValueError("last_seen must be >= first_seen")
        object.__setattr__(
            self,
            "skill_version_ref",
            optional_text(self.skill_version_ref, "skill_version_ref"),
        )
        object.__setattr__(
            self,
            "confidence",
            optional_unit_interval(self.confidence, "confidence"),
        )
        object.__setattr__(
            self,
            "priority",
            _optional_enum(self.priority, ImprovementPriority, "priority"),
        )
        object.__setattr__(self, "recurrence", derive_recurrence(self.recurrence))
        for field_name in ("repository_refs", "task_refs", "related_skill_ids", "aliases"):
            object.__setattr__(
                self,
                field_name,
                text_tuple(getattr(self, field_name), field_name),
            )
        relations = self.relations
        if not isinstance(relations, (list, tuple)):
            raise TypeError("relations must be a list or tuple")
        object.__setattr__(
            self,
            "relations",
            tuple(
                item if isinstance(item, ImprovementRelation) else ImprovementRelation.from_dict(item)
                for item in relations
            ),
        )
        work_refs = self.work_refs
        if not isinstance(work_refs, (list, tuple)):
            raise TypeError("work_refs must be a list or tuple")
        object.__setattr__(
            self,
            "work_refs",
            tuple(
                item if isinstance(item, ImprovementWorkRef) else ImprovementWorkRef.from_dict(item)
                for item in work_refs
            ),
        )
        merge_lineage = self.merge_lineage
        if not isinstance(merge_lineage, (list, tuple)):
            raise TypeError("merge_lineage must be a list or tuple")
        object.__setattr__(
            self,
            "merge_lineage",
            tuple(
                item
                if isinstance(item, ImprovementMergeLineage)
                else ImprovementMergeLineage.from_dict(item)
                for item in merge_lineage
            ),
        )
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise TypeError("revision must be an integer")
        if self.revision < 1:
            raise ValueError("revision must be >= 1")
        if self.temporal is not None and not isinstance(self.temporal, TemporalEnvelope):
            raise TypeError("temporal must be a TemporalEnvelope")
        if self.resolution is not None and not isinstance(self.resolution, ResolutionMeta):
            raise TypeError("resolution must be a ResolutionMeta")
        object.__setattr__(
            self,
            "superseded_by_improvement_id",
            optional_text(self.superseded_by_improvement_id, "superseded_by_improvement_id"),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "improvement_id": self.improvement_id,
            "skill_id": self.skill_id,
            "root_cause_key": self.root_cause_key,
            "summary": self.summary,
            "recommendation": self.recommendation,
            "expected_benefit": self.expected_benefit,
            "lifecycle": self.lifecycle.value,
            "first_seen": format_utc_datetime(self.first_seen),
            "last_seen": format_utc_datetime(self.last_seen),
            "recurrence": self.recurrence,
            "repository_refs": list(self.repository_refs),
            "task_refs": list(self.task_refs),
            "related_skill_ids": list(self.related_skill_ids),
            "relations": [item.to_dict() for item in self.relations],
            "work_refs": [item.to_dict() for item in self.work_refs],
            "merge_lineage": [item.to_dict() for item in self.merge_lineage],
            "revision": self.revision,
            "aliases": list(self.aliases),
        }
        if self.skill_version_ref is not None:
            payload["skill_version_ref"] = self.skill_version_ref
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.priority is not None:
            payload["priority"] = self.priority.value
        if self.temporal is not None:
            payload["temporal"] = self.temporal.to_dict()
        if self.resolution is not None:
            payload["resolution"] = self.resolution.to_dict()
        if self.superseded_by_improvement_id is not None:
            payload["superseded_by_improvement_id"] = self.superseded_by_improvement_id
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Improvement:
        raw_temporal = payload.get("temporal")
        raw_resolution = payload.get("resolution")
        return cls(
            schema_version=payload.get("schema_version", ""),
            improvement_id=payload.get("improvement_id", ""),
            skill_id=payload.get("skill_id", ""),
            root_cause_key=payload.get("root_cause_key", ""),
            summary=payload.get("summary", ""),
            recommendation=payload.get("recommendation", ""),
            expected_benefit=payload.get("expected_benefit", ""),
            lifecycle=payload.get("lifecycle", ""),
            first_seen=parse_utc_datetime(payload.get("first_seen"), "first_seen"),
            last_seen=parse_utc_datetime(payload.get("last_seen"), "last_seen"),
            skill_version_ref=payload.get("skill_version_ref"),
            confidence=payload.get("confidence"),
            priority=payload.get("priority"),
            recurrence=payload.get("recurrence", 0),
            repository_refs=payload.get("repository_refs", ()),
            task_refs=payload.get("task_refs", ()),
            related_skill_ids=payload.get("related_skill_ids", ()),
            relations=payload.get("relations", ()),
            work_refs=payload.get("work_refs", ()),
            merge_lineage=payload.get("merge_lineage", ()),
            revision=payload.get("revision", 1),
            temporal=(
                None
                if raw_temporal is None
                else TemporalEnvelope.from_dict(raw_temporal)
                if isinstance(raw_temporal, Mapping)
                else raw_temporal
            ),
            resolution=(
                None
                if raw_resolution is None
                else ResolutionMeta.from_dict(raw_resolution)
                if isinstance(raw_resolution, Mapping)
                else raw_resolution
            ),
            superseded_by_improvement_id=payload.get("superseded_by_improvement_id"),
            aliases=payload.get("aliases", ()),
        )


@dataclass(frozen=True, slots=True)
class ImprovementObservation:
    """Append-only Learning / Evidence event. Idempotent via idempotency_key."""

    schema_version: str
    observation_id: str
    agent_id: str
    run_id: str
    skill_id: str
    observation: str
    recommendation: str
    evidence: tuple[str, ...]
    timestamp: datetime
    idempotency_key: str
    improvement_id: str | None = None
    task_ref: str | None = None
    repository_ref: str | None = None
    skill_version_ref: str | None = None
    confidence: float | None = None
    root_cause_key: str | None = None
    provenance: Provenance | None = None
    temporal: TemporalEnvelope | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="improvement-observation",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "observation_id",
            required_text(self.observation_id, "observation_id"),
        )
        object.__setattr__(self, "agent_id", required_text(self.agent_id, "agent_id"))
        object.__setattr__(self, "run_id", required_text(self.run_id, "run_id"))
        object.__setattr__(self, "skill_id", required_text(self.skill_id, "skill_id"))
        object.__setattr__(
            self,
            "observation",
            required_text(self.observation, "observation"),
        )
        object.__setattr__(
            self,
            "recommendation",
            required_text(self.recommendation, "recommendation"),
        )
        object.__setattr__(self, "evidence", text_tuple(self.evidence, "evidence"))
        object.__setattr__(
            self,
            "timestamp",
            normalize_utc_datetime(self.timestamp, "timestamp"),
        )
        object.__setattr__(
            self,
            "idempotency_key",
            required_text(self.idempotency_key, "idempotency_key"),
        )
        object.__setattr__(
            self,
            "improvement_id",
            optional_text(self.improvement_id, "improvement_id"),
        )
        object.__setattr__(self, "task_ref", optional_text(self.task_ref, "task_ref"))
        object.__setattr__(
            self,
            "repository_ref",
            optional_text(self.repository_ref, "repository_ref"),
        )
        object.__setattr__(
            self,
            "skill_version_ref",
            optional_text(self.skill_version_ref, "skill_version_ref"),
        )
        object.__setattr__(
            self,
            "confidence",
            optional_unit_interval(self.confidence, "confidence"),
        )
        if self.root_cause_key is not None:
            object.__setattr__(
                self,
                "root_cause_key",
                normalize_root_cause_key(self.root_cause_key),
            )
        if self.provenance is not None and not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be a Provenance")
        if self.temporal is not None and not isinstance(self.temporal, TemporalEnvelope):
            raise TypeError("temporal must be a TemporalEnvelope")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "skill_id": self.skill_id,
            "observation": self.observation,
            "recommendation": self.recommendation,
            "evidence": list(self.evidence),
            "timestamp": format_utc_datetime(self.timestamp),
            "idempotency_key": self.idempotency_key,
        }
        for field_name in (
            "improvement_id",
            "task_ref",
            "repository_ref",
            "skill_version_ref",
            "root_cause_key",
        ):
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = value
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.provenance is not None:
            payload["provenance"] = self.provenance.to_dict()
        if self.temporal is not None:
            payload["temporal"] = self.temporal.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ImprovementObservation:
        raw_provenance = payload.get("provenance")
        raw_temporal = payload.get("temporal")
        return cls(
            schema_version=payload.get("schema_version", ""),
            observation_id=payload.get("observation_id", ""),
            agent_id=payload.get("agent_id", ""),
            run_id=payload.get("run_id", ""),
            skill_id=payload.get("skill_id", ""),
            observation=payload.get("observation", ""),
            recommendation=payload.get("recommendation", ""),
            evidence=payload.get("evidence", ()),
            timestamp=parse_utc_datetime(payload.get("timestamp"), "timestamp"),
            idempotency_key=payload.get("idempotency_key", ""),
            improvement_id=payload.get("improvement_id"),
            task_ref=payload.get("task_ref"),
            repository_ref=payload.get("repository_ref"),
            skill_version_ref=payload.get("skill_version_ref"),
            confidence=payload.get("confidence"),
            root_cause_key=payload.get("root_cause_key"),
            provenance=(
                None
                if raw_provenance is None
                else Provenance.from_dict(raw_provenance)
                if isinstance(raw_provenance, Mapping)
                else raw_provenance
            ),
            temporal=(
                None
                if raw_temporal is None
                else TemporalEnvelope.from_dict(raw_temporal)
                if isinstance(raw_temporal, Mapping)
                else raw_temporal
            ),
        )


__all__ = [
    "ALLOWED_LIFECYCLE_TRANSITIONS",
    "IMPROVEMENT_MERGE_LINEAGE_SCHEMA",
    "IMPROVEMENT_OBSERVATION_SCHEMA",
    "IMPROVEMENT_SCHEMA",
    "IMPROVEMENT_WORK_REF_SCHEMA",
    "DedupeRelationKind",
    "Improvement",
    "ImprovementLifecycle",
    "ImprovementMergeLineage",
    "ImprovementObservation",
    "ImprovementPriority",
    "ImprovementRelation",
    "ImprovementWorkRef",
    "WorkRefKind",
    "build_improvement_id",
    "derive_recurrence",
    "is_lifecycle_transition_allowed",
    "normalize_root_cause_key",
    "require_lifecycle_transition",
]
