"""Evidence, decisions, and trust contracts (Slice 8)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from agent_brain.contracts import (
    ArtifactRef,
    Provenance,
    ResolutionMeta,
    TemporalEnvelope,
)
from agent_brain.contracts._validation import (
    normalize_utc_datetime,
    parse_utc_datetime,
)
from agent_brain.contracts.versioning import require_compatible_version

EVIDENCE_STATE_SCHEMA = "evidence-state/v1"
CLAIM_STATE_SCHEMA = "claim-state/v1"
DECISION_RECORD_SCHEMA = "decision-record/v1"
EVIDENCE_QUERY_SCHEMA = "evidence-query/v1"
CLAIM_QUERY_SCHEMA = "claim-query/v1"
DECISION_QUERY_SCHEMA = "decision-query/v1"
DECISION_REPLAY_QUERY_SCHEMA = "decision-replay-query/v1"
TRUST_REQUEST_SCHEMA = "trust-request/v1"
EVIDENCE_RESOLUTION_SCHEMA = "evidence-resolution/v1"
CLAIM_RESOLUTION_SCHEMA = "claim-resolution/v1"
DECISION_HISTORY_RESULT_SCHEMA = "decision-history-result/v1"
DECISION_REPLAY_SCHEMA = "decision-replay/v1"
CONTRADICTION_FINDING_SCHEMA = "contradiction-finding/v1"
CONTRADICTION_SCAN_RESULT_SCHEMA = "contradiction-scan-result/v1"
STALE_FINDING_SCHEMA = "stale-finding/v1"
FRESHNESS_REPORT_SCHEMA = "freshness-report/v1"
RESOLUTION_STATE_ENTRY_SCHEMA = "resolution-state-entry/v1"
SCOPE_DRIFT_FINDING_SCHEMA = "scope-drift-finding/v1"
SCOPE_DRIFT_REPORT_SCHEMA = "scope-drift-report/v1"
SCOPE_DRIFT_BLOCKING_SCHEMA = "scope-drift-blocking/v1"
QUALITY_DIMENSION_SCORE_SCHEMA = "quality-dimension-score/v1"
QUALITY_ASSESSMENT_SCHEMA = "quality-assessment/v1"
TRUST_SUMMARY_SCHEMA = "trust-summary/v1"
QUALITY_POLICY_SCHEMA = "quality-policy/v1"
TRUST_POLICY_SCHEMA = "trust-policy/v1"
FRESHNESS_POLICY_SCHEMA = "freshness-policy/v1"
SCOPE_DRIFT_POLICY_SCHEMA = "scope-drift-policy/v1"
EVIDENCE_RESOLUTION_POLICY_SCHEMA = "evidence-resolution-policy/v1"
CLAIM_RESOLUTION_POLICY_SCHEMA = "claim-resolution-policy/v1"

EVIDENCE_STRENGTH_LEVELS = (
    "none",
    "weak",
    "moderate",
    "strong",
    "blocking_missing",
)
EVIDENCE_STATUSES = ("active", "revoked", "unknown")
CLAIM_STATUSES = (
    "unknown",
    "proposed",
    "supported",
    "weakly_supported",
    "disputed",
    "invalidated",
)
DECISION_STATUSES = ("unknown", "proposed", "accepted", "parked", "invalidated")
SEVERITY_LEVELS = ("info", "warning", "blocking")
FINDING_STATUSES = ("open", "resolved", "refreshed", "replaced")
QUALITY_GRADES = ("blocking", "watch", "weak", "good")
TRUST_LEVELS = ("strong", "partial", "insufficient")
EVIDENCE_SUFFICIENCY_LEVELS = ("sufficient", "partial", "insufficient")
CONTRADICTION_TYPES = (
    "claim_vs_evidence",
    "decision_vs_evidence",
    "stale_decision_vs_new_evidence",
    "cross_provenance_conflict",
)
STALE_TYPES = (
    "source_hash_changed",
    "source_deleted",
    "validity_window_closed",
    "dependency_edge_no_longer_observed",
    "stale_context_package",
    "stale_briefing",
)
SCOPE_DRIFT_TYPES = (
    "path_out_of_scope",
    "forbidden_surface_touched",
    "runtime_surface_touched",
    "write_intent_without_authorization_ref",
    "write_mode_without_authorization_ref",
    "domain_out_of_scope",
    "issue_out_of_scope",
    "unexpected_dependency_expansion",
)

_QUERY_LIMIT_MIN = 1
_QUERY_LIMIT_MAX = 10_000


class EvidenceError(ValueError):
    """Base error for slice 8 evidence layer."""


class ResolutionError(EvidenceError):
    """Resolution input or query errors."""


class DecisionError(EvidenceError):
    """Decision history or replay errors."""


class ContradictionError(EvidenceError):
    """Contradiction scan errors."""


class FreshnessError(EvidenceError):
    """Freshness evaluation errors."""


class ScopeDriftError(EvidenceError):
    """Scope drift detection errors."""


class QualityError(EvidenceError):
    """Quality scoring errors."""


class TrustError(EvidenceError):
    """Trust summary errors."""


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


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(item, field_name) for item in values)


def _non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must not be negative")
    return value


def _positive_int(value: object, field_name: str) -> int:
    result = _non_negative_int(value, field_name)
    if result <= 0:
        raise ValueError(f"{field_name} must be positive")
    return result


def _score(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{field_name} must be a finite number between 0.0 and 1.0")
    return result


def _non_negative_finite_weight(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{field_name} must be a finite number >= 0.0")
    return result


def _normalize_utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return normalize_utc_datetime(value, field_name)
    if isinstance(value, str):
        return parse_utc_datetime(value, field_name)
    raise TypeError(f"{field_name} must be a datetime or ISO datetime string")


def _readonly_mapping(values: Mapping[str, float]) -> Mapping[str, float]:
    return MappingProxyType(dict(values))


def compute_weighted_mean(pairs: tuple[tuple[float, float], ...]) -> float | None:
    """Deterministic weighted mean; returns None when no positive weight."""
    weighted = [(value, weight) for value, weight in pairs if weight > 0.0]
    if not weighted:
        return None
    total_weight = sum(weight for _, weight in weighted)
    if total_weight <= 0.0:
        return None
    return sum(value * weight for value, weight in weighted) / total_weight


def _validate_vocab(value: str, field_name: str, vocabulary: tuple[str, ...]) -> str:
    normalized = _required_text(value, field_name)
    if normalized not in vocabulary:
        raise ValueError(f"{field_name} must be one of {vocabulary}")
    return normalized


@dataclass(frozen=True, slots=True)
class SourceState:
    source_ref: str
    source_hash: str | None = None
    observed: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_ref", _required_text(self.source_ref, "source_ref"))
        object.__setattr__(
            self,
            "source_hash",
            _optional_text(self.source_hash, "source_hash"),
        )


@dataclass(frozen=True, slots=True)
class ArtifactState:
    ref: ArtifactRef
    artifact_type: str
    temporal: TemporalEnvelope
    snapshot_identity: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.ref, ArtifactRef):
            raise TypeError("ref must be an ArtifactRef")
        if not isinstance(self.temporal, TemporalEnvelope):
            raise TypeError("temporal must be a TemporalEnvelope")
        object.__setattr__(
            self,
            "artifact_type",
            _required_text(self.artifact_type, "artifact_type"),
        )
        object.__setattr__(
            self,
            "snapshot_identity",
            _optional_text(self.snapshot_identity, "snapshot_identity"),
        )


@dataclass(frozen=True, slots=True)
class SurfaceState:
    surface_id: str
    surface_type: str
    operation_mode: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "surface_id", _required_text(self.surface_id, "surface_id"))
        object.__setattr__(
            self,
            "surface_type",
            _required_text(self.surface_type, "surface_type"),
        )
        object.__setattr__(
            self,
            "operation_mode",
            _optional_text(self.operation_mode, "operation_mode"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceState:
    schema_version: str
    evidence_id: str
    temporal: TemporalEnvelope
    provenance: Provenance
    resolution_meta: ResolutionMeta
    strength: str
    status: str

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="evidence-state",
            supported_major=1,
        )
        object.__setattr__(self, "evidence_id", _required_text(self.evidence_id, "evidence_id"))
        if not isinstance(self.temporal, TemporalEnvelope):
            raise TypeError("temporal must be a TemporalEnvelope")
        if not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be a Provenance")
        if not isinstance(self.resolution_meta, ResolutionMeta):
            raise TypeError("resolution_meta must be a ResolutionMeta")
        object.__setattr__(
            self,
            "strength",
            _validate_vocab(self.strength, "strength", EVIDENCE_STRENGTH_LEVELS),
        )
        object.__setattr__(
            self,
            "status",
            _validate_vocab(self.status, "status", EVIDENCE_STATUSES),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "temporal": self.temporal.to_dict(),
            "provenance": self.provenance.to_dict(),
            "resolution_meta": self.resolution_meta.to_dict(),
            "strength": self.strength,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EvidenceState:
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            evidence_id=str(payload.get("evidence_id", "")),
            temporal=TemporalEnvelope.from_dict(payload.get("temporal", {})),
            provenance=Provenance.from_dict(payload.get("provenance", {})),
            resolution_meta=ResolutionMeta.from_dict(payload.get("resolution_meta", {})),
            strength=str(payload.get("strength", "weak")),
            status=str(payload.get("status", "unknown")),
        )


@dataclass(frozen=True, slots=True)
class ClaimState:
    schema_version: str
    claim_id: str
    temporal: TemporalEnvelope
    provenance: Provenance
    resolution_meta: ResolutionMeta
    status: str
    scope: str = ""
    topics: tuple[str, ...] = ()
    uncertainty: float | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="claim-state",
            supported_major=1,
        )
        object.__setattr__(self, "claim_id", _required_text(self.claim_id, "claim_id"))
        if not isinstance(self.temporal, TemporalEnvelope):
            raise TypeError("temporal must be a TemporalEnvelope")
        if not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be a Provenance")
        if not isinstance(self.resolution_meta, ResolutionMeta):
            raise TypeError("resolution_meta must be a ResolutionMeta")
        object.__setattr__(
            self,
            "status",
            _validate_vocab(self.status, "status", CLAIM_STATUSES),
        )
        object.__setattr__(self, "scope", _required_text(self.scope, "scope") if self.scope else "")
        object.__setattr__(self, "topics", _text_tuple(self.topics, "topics"))
        if self.uncertainty is not None:
            object.__setattr__(self, "uncertainty", _score(self.uncertainty, "uncertainty"))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "claim_id": self.claim_id,
            "temporal": self.temporal.to_dict(),
            "provenance": self.provenance.to_dict(),
            "resolution_meta": self.resolution_meta.to_dict(),
            "status": self.status,
            "scope": self.scope,
            "topics": list(self.topics),
        }
        if self.uncertainty is not None:
            payload["uncertainty"] = self.uncertainty
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ClaimState:
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            claim_id=str(payload.get("claim_id", "")),
            temporal=TemporalEnvelope.from_dict(payload.get("temporal", {})),
            provenance=Provenance.from_dict(payload.get("provenance", {})),
            resolution_meta=ResolutionMeta.from_dict(payload.get("resolution_meta", {})),
            status=str(payload.get("status", "unknown")),
            scope=str(payload.get("scope", "")),
            topics=tuple(payload.get("topics") or ()),
            uncertainty=payload.get("uncertainty"),
        )


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    schema_version: str
    decision_id: str
    temporal: TemporalEnvelope
    provenance: Provenance
    resolution_meta: ResolutionMeta
    title: str
    question: str
    answer: str
    decision_type: str
    status: str
    scope: str = ""
    topics: tuple[str, ...] = ()
    issue_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    claim_refs: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    agent: str | None = None
    authorization_refs: tuple[str, ...] = ()
    requires_evidence: bool = False

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="decision-record",
            supported_major=1,
        )
        object.__setattr__(self, "decision_id", _required_text(self.decision_id, "decision_id"))
        if not isinstance(self.temporal, TemporalEnvelope):
            raise TypeError("temporal must be a TemporalEnvelope")
        if not isinstance(self.provenance, Provenance):
            raise TypeError("provenance must be a Provenance")
        if not isinstance(self.resolution_meta, ResolutionMeta):
            raise TypeError("resolution_meta must be a ResolutionMeta")
        for field_name in ("title", "question", "answer", "decision_type"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "status",
            _validate_vocab(self.status, "status", DECISION_STATUSES),
        )
        object.__setattr__(self, "scope", _required_text(self.scope, "scope") if self.scope else "")
        object.__setattr__(self, "topics", _text_tuple(self.topics, "topics"))
        for field_name in ("issue_refs", "evidence_refs", "claim_refs", "artifact_refs"):
            object.__setattr__(self, field_name, _text_tuple(getattr(self, field_name), field_name))
        object.__setattr__(self, "agent", _optional_text(self.agent, "agent"))
        object.__setattr__(
            self,
            "authorization_refs",
            _text_tuple(self.authorization_refs, "authorization_refs"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "temporal": self.temporal.to_dict(),
            "provenance": self.provenance.to_dict(),
            "resolution_meta": self.resolution_meta.to_dict(),
            "title": self.title,
            "question": self.question,
            "answer": self.answer,
            "decision_type": self.decision_type,
            "status": self.status,
            "scope": self.scope,
            "topics": list(self.topics),
            "issue_refs": list(self.issue_refs),
            "evidence_refs": list(self.evidence_refs),
            "claim_refs": list(self.claim_refs),
            "artifact_refs": list(self.artifact_refs),
            "agent": self.agent,
            "authorization_refs": list(self.authorization_refs),
            "requires_evidence": self.requires_evidence,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DecisionRecord:
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            decision_id=str(payload.get("decision_id", "")),
            temporal=TemporalEnvelope.from_dict(payload.get("temporal", {})),
            provenance=Provenance.from_dict(payload.get("provenance", {})),
            resolution_meta=ResolutionMeta.from_dict(payload.get("resolution_meta", {})),
            title=str(payload.get("title", "")),
            question=str(payload.get("question", "")),
            answer=str(payload.get("answer", "")),
            decision_type=str(payload.get("decision_type", "")),
            status=str(payload.get("status", "unknown")),
            scope=str(payload.get("scope", "")),
            topics=tuple(payload.get("topics") or ()),
            issue_refs=tuple(payload.get("issue_refs") or ()),
            evidence_refs=tuple(payload.get("evidence_refs") or ()),
            claim_refs=tuple(payload.get("claim_refs") or ()),
            artifact_refs=tuple(payload.get("artifact_refs") or ()),
            agent=payload.get("agent"),
            authorization_refs=tuple(payload.get("authorization_refs") or ()),
            requires_evidence=bool(payload.get("requires_evidence", False)),
        )


def _validate_query_limit(limit: int) -> int:
    if limit < _QUERY_LIMIT_MIN or limit > _QUERY_LIMIT_MAX:
        raise ResolutionError(f"limit must be within {_QUERY_LIMIT_MIN}..{_QUERY_LIMIT_MAX}")
    return limit


EVIDENCE_QUERY_MODES = frozenset(
    {
        "by_evidence_id",
        "by_artifact",
        "by_claim",
        "by_decision",
        "by_source",
        "by_evidence_type",
        "by_strength",
        "by_status",
    }
)

CLAIM_QUERY_MODES = frozenset(
    {
        "by_claim_id",
        "by_topic",
        "by_scope",
        "by_status",
        "by_artifact",
        "by_evidence_ref",
        "by_decision_ref",
    }
)


@dataclass(frozen=True, slots=True)
class EvidenceQuery:
    schema_version: str
    mode: str
    limit: int = 200
    evidence_id: str | None = None
    artifact: str | None = None
    claim: str | None = None
    decision: str | None = None
    source: str | None = None
    evidence_type: str | None = None
    strength: str | None = None
    status: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="evidence-query",
            supported_major=1,
        )
        object.__setattr__(self, "mode", _required_text(self.mode, "mode"))
        if self.mode not in EVIDENCE_QUERY_MODES:
            raise ResolutionError(f"unsupported evidence query mode: {self.mode}")
        object.__setattr__(self, "limit", _validate_query_limit(self.limit))
        selectors = {
            "by_evidence_id": self.evidence_id,
            "by_artifact": self.artifact,
            "by_claim": self.claim,
            "by_decision": self.decision,
            "by_source": self.source,
            "by_evidence_type": self.evidence_type,
            "by_strength": self.strength,
            "by_status": self.status,
        }
        required = selectors.get(self.mode)
        if required is None or not str(required).strip():
            raise ResolutionError(f"missing required selector for mode {self.mode}")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "limit": self.limit,
        }
        for key in (
            "evidence_id",
            "artifact",
            "claim",
            "decision",
            "source",
            "evidence_type",
            "strength",
            "status",
        ):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EvidenceQuery:
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            mode=str(payload.get("mode", "")),
            limit=int(payload.get("limit", 200)),
            evidence_id=payload.get("evidence_id"),
            artifact=payload.get("artifact"),
            claim=payload.get("claim"),
            decision=payload.get("decision"),
            source=payload.get("source"),
            evidence_type=payload.get("evidence_type"),
            strength=payload.get("strength"),
            status=payload.get("status"),
        )


@dataclass(frozen=True, slots=True)
class ClaimQuery:
    schema_version: str
    mode: str
    limit: int = 200
    claim_id: str | None = None
    topic: str | None = None
    scope: str | None = None
    status: str | None = None
    artifact: str | None = None
    evidence_ref: str | None = None
    decision_ref: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="claim-query",
            supported_major=1,
        )
        object.__setattr__(self, "mode", _required_text(self.mode, "mode"))
        if self.mode not in CLAIM_QUERY_MODES:
            raise ResolutionError(f"unsupported claim query mode: {self.mode}")
        object.__setattr__(self, "limit", _validate_query_limit(self.limit))
        selectors = {
            "by_claim_id": self.claim_id,
            "by_topic": self.topic,
            "by_scope": self.scope,
            "by_status": self.status,
            "by_artifact": self.artifact,
            "by_evidence_ref": self.evidence_ref,
            "by_decision_ref": self.decision_ref,
        }
        required = selectors.get(self.mode)
        if required is None or not str(required).strip():
            raise ResolutionError(f"missing required selector for mode {self.mode}")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "limit": self.limit,
        }
        for key in (
            "claim_id",
            "topic",
            "scope",
            "status",
            "artifact",
            "evidence_ref",
            "decision_ref",
        ):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ClaimQuery:
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            mode=str(payload.get("mode", "")),
            limit=int(payload.get("limit", 200)),
            claim_id=payload.get("claim_id"),
            topic=payload.get("topic"),
            scope=payload.get("scope"),
            status=payload.get("status"),
            artifact=payload.get("artifact"),
            evidence_ref=payload.get("evidence_ref"),
            decision_ref=payload.get("decision_ref"),
        )


@dataclass(frozen=True, slots=True)
class DecisionQuery:
    schema_version: str
    mode: str
    limit: int = 200
    decision_id: str | None = None
    scope: str | None = None
    status: str | None = None
    topic: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="decision-query",
            supported_major=1,
        )
        object.__setattr__(self, "mode", _required_text(self.mode, "mode"))
        object.__setattr__(self, "limit", _validate_query_limit(self.limit))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "limit": self.limit,
            "decision_id": self.decision_id,
            "scope": self.scope,
            "status": self.status,
            "topic": self.topic,
        }


@dataclass(frozen=True, slots=True)
class DecisionReplayQuery:
    schema_version: str
    decision_id: str
    include_chain: bool = True

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="decision-replay-query",
            supported_major=1,
        )
        object.__setattr__(self, "decision_id", _required_text(self.decision_id, "decision_id"))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "include_chain": self.include_chain,
        }


@dataclass(frozen=True, slots=True)
class TrustRequest:
    schema_version: str
    scope: str
    topic: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="trust-request",
            supported_major=1,
        )
        object.__setattr__(self, "scope", _required_text(self.scope, "scope"))
        object.__setattr__(self, "topic", _optional_text(self.topic, "topic"))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "scope": self.scope,
        }
        if self.topic is not None:
            payload["topic"] = self.topic
        return payload


@dataclass(frozen=True, slots=True)
class QualityPolicy:
    schema_version: str
    dimension_weights: Mapping[str, float]
    grade_bands: Mapping[str, float]
    severity_penalties: Mapping[str, float]
    dependency_confidence_threshold: float
    finding_exempt_statuses: tuple[str, ...] = ("resolved", "refreshed", "replaced")

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="quality-policy",
            supported_major=1,
        )
        weights = {
            key: _non_negative_finite_weight(value, f"dimension_weights[{key}]")
            for key, value in dict(self.dimension_weights).items()
        }
        object.__setattr__(self, "dimension_weights", _readonly_mapping(weights))
        bands = {
            key: _score(value, f"grade_bands[{key}]")
            for key, value in dict(self.grade_bands).items()
        }
        object.__setattr__(self, "grade_bands", _readonly_mapping(bands))
        penalties = {
            key: _score(value, f"severity_penalties[{key}]")
            for key, value in dict(self.severity_penalties).items()
        }
        object.__setattr__(self, "severity_penalties", _readonly_mapping(penalties))
        object.__setattr__(
            self,
            "dependency_confidence_threshold",
            _score(self.dependency_confidence_threshold, "dependency_confidence_threshold"),
        )
        object.__setattr__(
            self,
            "finding_exempt_statuses",
            _text_tuple(self.finding_exempt_statuses, "finding_exempt_statuses"),
        )

    @classmethod
    def default(cls) -> QualityPolicy:
        dimensions = (
            "coverage",
            "freshness",
            "evidence",
            "contradiction",
            "dependency_confidence",
            "decision_validity",
            "scope_risk",
        )
        return cls(
            schema_version=QUALITY_POLICY_SCHEMA,
            dimension_weights={name: 1.0 for name in dimensions},
            grade_bands={
                "blocking": 0.30,
                "watch": 0.50,
                "weak": 0.70,
                "good": 0.70,
            },
            severity_penalties={"blocking": 0.50, "warning": 0.25, "info": 0.0},
            dependency_confidence_threshold=0.5,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "dimension_weights": dict(self.dimension_weights),
            "grade_bands": dict(self.grade_bands),
            "severity_penalties": dict(self.severity_penalties),
            "dependency_confidence_threshold": self.dependency_confidence_threshold,
            "finding_exempt_statuses": list(self.finding_exempt_statuses),
        }


@dataclass(frozen=True, slots=True)
class TrustPolicy:
    schema_version: str
    component_weights: Mapping[str, float]
    level_thresholds: Mapping[str, float]
    required_components: tuple[str, ...] = ("evidence", "claims", "decisions")

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="trust-policy",
            supported_major=1,
        )
        weights = {
            key: _non_negative_finite_weight(value, f"component_weights[{key}]")
            for key, value in dict(self.component_weights).items()
        }
        object.__setattr__(self, "component_weights", _readonly_mapping(weights))
        thresholds = {
            key: _score(value, f"level_thresholds[{key}]")
            for key, value in dict(self.level_thresholds).items()
        }
        object.__setattr__(self, "level_thresholds", _readonly_mapping(thresholds))
        object.__setattr__(
            self,
            "required_components",
            _text_tuple(self.required_components, "required_components"),
        )

    @classmethod
    def default(cls) -> TrustPolicy:
        return cls(
            schema_version=TRUST_POLICY_SCHEMA,
            component_weights={"evidence": 1.0, "claims": 1.0, "decisions": 1.0},
            level_thresholds={"strong": 0.80, "partial": 0.50},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "component_weights": dict(self.component_weights),
            "level_thresholds": dict(self.level_thresholds),
            "required_components": list(self.required_components),
        }


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    schema_version: str
    default_freshness_window_seconds: int
    exempt_statuses: tuple[str, ...] = ("resolved", "refreshed", "replaced")

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="freshness-policy",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "default_freshness_window_seconds",
            _positive_int(self.default_freshness_window_seconds, "default_freshness_window_seconds"),
        )
        object.__setattr__(self, "exempt_statuses", _text_tuple(self.exempt_statuses, "exempt_statuses"))

    @classmethod
    def default(cls) -> FreshnessPolicy:
        return cls(
            schema_version=FRESHNESS_POLICY_SCHEMA,
            default_freshness_window_seconds=86_400,
        )


@dataclass(frozen=True, slots=True)
class ScopeDriftPolicy:
    schema_version: str
    target_paths: tuple[str, ...] = ()
    allowed_domains: tuple[str, ...] = ()
    allowed_issues: tuple[str, ...] = ()
    forbidden_surfaces: tuple[str, ...] = ()
    protected_surface_types: tuple[str, ...] = ()
    write_like_operation_modes: tuple[str, ...] = ()
    max_artifact_count: int = 20
    default_recommended_reads: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="scope-drift-policy",
            supported_major=1,
        )
        for field_name in (
            "target_paths",
            "allowed_domains",
            "allowed_issues",
            "forbidden_surfaces",
            "protected_surface_types",
            "write_like_operation_modes",
            "default_recommended_reads",
        ):
            object.__setattr__(self, field_name, _text_tuple(getattr(self, field_name), field_name))
        object.__setattr__(self, "max_artifact_count", _positive_int(self.max_artifact_count, "max_artifact_count"))

    @classmethod
    def default(cls) -> ScopeDriftPolicy:
        return cls(schema_version=SCOPE_DRIFT_POLICY_SCHEMA)


@dataclass(frozen=True, slots=True)
class EvidenceResolutionPolicy:
    schema_version: str
    acceptable_strengths: tuple[str, ...]
    default_strength: str

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="evidence-resolution-policy",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "acceptable_strengths",
            _text_tuple(self.acceptable_strengths, "acceptable_strengths"),
        )
        object.__setattr__(
            self,
            "default_strength",
            _validate_vocab(self.default_strength, "default_strength", EVIDENCE_STRENGTH_LEVELS),
        )

    @classmethod
    def default(cls) -> EvidenceResolutionPolicy:
        return cls(
            schema_version=EVIDENCE_RESOLUTION_POLICY_SCHEMA,
            acceptable_strengths=("moderate", "strong"),
            default_strength="weak",
        )


@dataclass(frozen=True, slots=True)
class ClaimResolutionPolicy:
    schema_version: str
    statuses_requiring_evidence: tuple[str, ...]
    blocking_statuses: tuple[str, ...]

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="claim-resolution-policy",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "statuses_requiring_evidence",
            _text_tuple(self.statuses_requiring_evidence, "statuses_requiring_evidence"),
        )
        object.__setattr__(
            self,
            "blocking_statuses",
            _text_tuple(self.blocking_statuses, "blocking_statuses"),
        )

    @classmethod
    def default(cls) -> ClaimResolutionPolicy:
        return cls(
            schema_version=CLAIM_RESOLUTION_POLICY_SCHEMA,
            statuses_requiring_evidence=("supported", "weakly_supported"),
            blocking_statuses=("disputed", "invalidated"),
        )


# Re-export result contracts so consumers can import from contract.py.
from agent_brain.evidence.contract_results import (
    ClaimResolution,
    ContradictionFinding,
    ContradictionScanResult,
    DecisionHistoryResult,
    DecisionReplay,
    EvidenceResolution,
    FreshnessReport,
    QualityAssessment,
    QualityDimensionScore,
    ResolutionStateEntry,
    ScopeDriftBlocking,
    ScopeDriftFinding,
    ScopeDriftReport,
    StaleFinding,
    TrustSummary,
)

__all__ = [
    "ClaimResolution",
    "ContradictionFinding",
    "ContradictionScanResult",
    "DecisionHistoryResult",
    "DecisionReplay",
    "EvidenceResolution",
    "FreshnessReport",
    "QualityAssessment",
    "QualityDimensionScore",
    "ResolutionStateEntry",
    "ScopeDriftBlocking",
    "ScopeDriftFinding",
    "ScopeDriftReport",
    "StaleFinding",
    "TrustSummary",
]

