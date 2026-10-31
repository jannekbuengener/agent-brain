"""Slice 8 result contracts (split from contract.py for maintainability)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from agent_brain.contracts import ResolutionState
from agent_brain.contracts._validation import format_utc_datetime
from agent_brain.contracts.versioning import require_compatible_version

from agent_brain.contracts._validation import normalize_utc_datetime, parse_utc_datetime
from agent_brain.evidence._shared import (
    FINDING_STATUSES,
    QUALITY_GRADES,
    SEVERITY_LEVELS,
    TRUST_LEVELS,
    required_text,
    score,
    text_tuple,
    validate_vocab,
)


def _normalize_utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return normalize_utc_datetime(value, field_name)
    if isinstance(value, str):
        return parse_utc_datetime(value, field_name)
    raise TypeError(f"{field_name} must be a datetime or ISO datetime string")


@dataclass(frozen=True, slots=True)
class EvidenceResolution:
    schema_version: str
    matched_evidence_ids: tuple[str, ...]
    by_status: Mapping[str, tuple[str, ...]]
    by_strength: Mapping[str, tuple[str, ...]]
    conflicting_evidence_ids: tuple[tuple[str, ...], ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="evidence-resolution",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "matched_evidence_ids",
            text_tuple(self.matched_evidence_ids, "matched_evidence_ids"),
        )
        if not self.limitations:
            raise ValueError("limitations must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "matched_evidence_ids": list(self.matched_evidence_ids),
            "by_status": {key: list(value) for key, value in self.by_status.items()},
            "by_strength": {key: list(value) for key, value in self.by_strength.items()},
            "conflicting_evidence_ids": [list(group) for group in self.conflicting_evidence_ids],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class ClaimResolution:
    schema_version: str
    matched_claim_ids: tuple[str, ...]
    by_status: Mapping[str, tuple[str, ...]]
    disputed_claim_ids: tuple[str, ...]
    invalidated_claim_ids: tuple[str, ...]
    missing_evidence_claim_ids: tuple[str, ...]
    unresolved_evidence_refs: tuple[str, ...]
    conflicting_claim_ids: tuple[tuple[str, ...], ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="claim-resolution",
            supported_major=1,
        )
        if not self.limitations:
            raise ValueError("limitations must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "matched_claim_ids": list(self.matched_claim_ids),
            "by_status": {key: list(value) for key, value in self.by_status.items()},
            "disputed_claim_ids": list(self.disputed_claim_ids),
            "invalidated_claim_ids": list(self.invalidated_claim_ids),
            "missing_evidence_claim_ids": list(self.missing_evidence_claim_ids),
            "unresolved_evidence_refs": list(self.unresolved_evidence_refs),
            "conflicting_claim_ids": [list(group) for group in self.conflicting_claim_ids],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class DecisionHistoryResult:
    schema_version: str
    current_decision_ids: tuple[str, ...]
    superseded_decision_ids: tuple[str, ...]
    invalidated_decision_ids: tuple[str, ...]
    unresolved_decision_ids: tuple[str, ...]
    supersession_chains: tuple[tuple[str, ...], ...]
    unresolved_evidence_refs: tuple[str, ...]
    unresolved_claim_refs: tuple[str, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="decision-history-result",
            supported_major=1,
        )
        if not self.limitations:
            raise ValueError("limitations must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "current_decision_ids": list(self.current_decision_ids),
            "superseded_decision_ids": list(self.superseded_decision_ids),
            "invalidated_decision_ids": list(self.invalidated_decision_ids),
            "unresolved_decision_ids": list(self.unresolved_decision_ids),
            "supersession_chains": [list(chain) for chain in self.supersession_chains],
            "unresolved_evidence_refs": list(self.unresolved_evidence_refs),
            "unresolved_claim_refs": list(self.unresolved_claim_refs),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class DecisionReplay:
    schema_version: str
    decision_id: str
    chain: tuple[str, ...]
    decision_chain_hash: str
    authorization_implied: bool
    authorization_refs: tuple[str, ...]
    unresolved_evidence_refs: tuple[str, ...]
    unresolved_claim_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    as_of: datetime

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="decision-replay",
            supported_major=1,
        )
        object.__setattr__(self, "decision_id", required_text(self.decision_id, "decision_id"))
        if self.authorization_implied:
            raise ValueError("authorization_implied must be False")
        if not self.limitations:
            raise ValueError("limitations must not be empty")
        object.__setattr__(self, "as_of", _normalize_utc_datetime(self.as_of, "as_of"))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "chain": list(self.chain),
            "decision_chain_hash": self.decision_chain_hash,
            "authorization_implied": self.authorization_implied,
            "authorization_refs": list(self.authorization_refs),
            "unresolved_evidence_refs": list(self.unresolved_evidence_refs),
            "unresolved_claim_refs": list(self.unresolved_claim_refs),
            "limitations": list(self.limitations),
            "as_of": format_utc_datetime(self.as_of),
        }


@dataclass(frozen=True, slots=True)
class ContradictionFinding:
    schema_version: str
    finding_id: str
    rule_id: str
    rule_type: str
    severity: str
    confidence: float
    status: str
    detected_at: datetime
    explanation: str
    recommendation: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="contradiction-finding",
            supported_major=1,
        )
        object.__setattr__(self, "finding_id", required_text(self.finding_id, "finding_id"))
        object.__setattr__(self, "severity", validate_vocab(self.severity, "severity", SEVERITY_LEVELS))
        object.__setattr__(self, "status", validate_vocab(self.status, "status", FINDING_STATUSES))
        object.__setattr__(self, "confidence", score(self.confidence, "confidence"))
        object.__setattr__(self, "detected_at", _normalize_utc_datetime(self.detected_at, "detected_at"))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "severity": self.severity,
            "confidence": self.confidence,
            "status": self.status,
            "detected_at": format_utc_datetime(self.detected_at),
            "explanation": self.explanation,
        }
        if self.recommendation is not None:
            payload["recommendation"] = self.recommendation
        return payload


@dataclass(frozen=True, slots=True)
class ContradictionScanResult:
    schema_version: str
    findings: tuple[ContradictionFinding, ...]
    blocking_count: int
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="contradiction-scan-result",
            supported_major=1,
        )
        if not self.limitations:
            raise ValueError("limitations must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "findings": [item.to_dict() for item in self.findings],
            "blocking_count": self.blocking_count,
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class StaleFinding:
    schema_version: str
    finding_id: str
    stale_type: str
    severity: str
    status: str
    detected_at: datetime
    entity_ref: str
    explanation: str

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="stale-finding",
            supported_major=1,
        )
        object.__setattr__(self, "stale_type", required_text(self.stale_type, "stale_type"))
        object.__setattr__(self, "severity", validate_vocab(self.severity, "severity", SEVERITY_LEVELS))
        object.__setattr__(self, "status", validate_vocab(self.status, "status", FINDING_STATUSES))
        object.__setattr__(self, "detected_at", _normalize_utc_datetime(self.detected_at, "detected_at"))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "finding_id": self.finding_id,
            "stale_type": self.stale_type,
            "severity": self.severity,
            "status": self.status,
            "detected_at": format_utc_datetime(self.detected_at),
            "entity_ref": self.entity_ref,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class ResolutionStateEntry:
    schema_version: str
    ref: str
    entity_kind: str
    resolution_state: ResolutionState
    reason_code: str
    explanation: str

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="resolution-state-entry",
            supported_major=1,
        )
        if not isinstance(self.resolution_state, ResolutionState):
            raise TypeError("resolution_state must be a ResolutionState")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "ref": self.ref,
            "entity_kind": self.entity_kind,
            "resolution_state": self.resolution_state.value,
            "reason_code": self.reason_code,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class FreshnessReport:
    schema_version: str
    stale_findings: tuple[StaleFinding, ...]
    resolution_states: tuple[ResolutionStateEntry, ...]
    recommended_refresh: tuple[str, ...]
    system_as_of: datetime | None
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="freshness-report",
            supported_major=1,
        )
        if not self.limitations:
            raise ValueError("limitations must not be empty")
        if self.system_as_of is not None:
            object.__setattr__(
                self,
                "system_as_of",
                _normalize_utc_datetime(self.system_as_of, "system_as_of"),
            )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "stale_findings": [item.to_dict() for item in self.stale_findings],
            "resolution_states": [item.to_dict() for item in self.resolution_states],
            "recommended_refresh": list(self.recommended_refresh),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }
        if self.system_as_of is not None:
            payload["system_as_of"] = format_utc_datetime(self.system_as_of)
        return payload


@dataclass(frozen=True, slots=True)
class ScopeDriftFinding:
    schema_version: str
    finding_id: str
    drift_type: str
    severity: str
    status: str
    detected_at: datetime
    explanation: str

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="scope-drift-finding",
            supported_major=1,
        )
        object.__setattr__(self, "drift_type", required_text(self.drift_type, "drift_type"))
        object.__setattr__(self, "severity", validate_vocab(self.severity, "severity", SEVERITY_LEVELS))
        object.__setattr__(self, "status", validate_vocab(self.status, "status", FINDING_STATUSES))
        object.__setattr__(self, "detected_at", _normalize_utc_datetime(self.detected_at, "detected_at"))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "finding_id": self.finding_id,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "status": self.status,
            "detected_at": format_utc_datetime(self.detected_at),
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class ScopeDriftReport:
    schema_version: str
    findings: tuple[ScopeDriftFinding, ...]
    blocking_count: int
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="scope-drift-report",
            supported_major=1,
        )
        if not self.limitations:
            raise ValueError("limitations must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "findings": [item.to_dict() for item in self.findings],
            "blocking_count": self.blocking_count,
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class ScopeDriftBlocking:
    schema_version: str
    blocking: bool
    blocking_count: int
    summary: str
    affected_artifact_refs: tuple[str, ...]
    findings: tuple[ScopeDriftFinding, ...]
    recommended_actions: tuple[str, ...]
    recommended_next_reads: tuple[str, ...]

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="scope-drift-blocking",
            supported_major=1,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "blocking": self.blocking,
            "blocking_count": self.blocking_count,
            "summary": self.summary,
            "affected_artifact_refs": list(self.affected_artifact_refs),
            "findings": [item.to_dict() for item in self.findings],
            "recommended_actions": list(self.recommended_actions),
            "recommended_next_reads": list(self.recommended_next_reads),
        }


@dataclass(frozen=True, slots=True)
class QualityDimensionScore:
    schema_version: str
    dimension: str
    score: float
    grade: str
    explanation: str
    inputs_used: int
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="quality-dimension-score",
            supported_major=1,
        )
        object.__setattr__(self, "grade", validate_vocab(self.grade, "grade", QUALITY_GRADES))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "dimension": self.dimension,
            "score": self.score,
            "grade": self.grade,
            "explanation": self.explanation,
            "inputs_used": self.inputs_used,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    schema_version: str
    scope_id: str
    level: str
    scored_at: datetime
    overall_score: float
    overall_grade: str
    dimensions: tuple[QualityDimensionScore, ...]
    limitations: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="quality-assessment",
            supported_major=1,
        )
        if not self.limitations:
            raise ValueError("limitations must not be empty")
        object.__setattr__(self, "scored_at", _normalize_utc_datetime(self.scored_at, "scored_at"))
        object.__setattr__(
            self,
            "overall_grade",
            validate_vocab(self.overall_grade, "overall_grade", QUALITY_GRADES),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "scope_id": self.scope_id,
            "level": self.level,
            "scored_at": format_utc_datetime(self.scored_at),
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade,
            "dimensions": [item.to_dict() for item in self.dimensions],
            "limitations": list(self.limitations),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class TrustSummary:
    schema_version: str
    trust_level: str
    composite_score: float | None
    evidence_sufficiency: str
    component_scores: Mapping[str, float | None]
    source_trust_assessment: Mapping[str, object]
    confidence_assessment: Mapping[str, object]
    blocking_findings: tuple[Mapping[str, object], ...]
    limitations: tuple[str, ...]
    assessed_at: datetime | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="trust-summary",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "trust_level",
            validate_vocab(self.trust_level, "trust_level", TRUST_LEVELS),
        )
        if not self.limitations:
            raise ValueError("limitations must not be empty")
        if self.assessed_at is not None:
            object.__setattr__(self, "assessed_at", _normalize_utc_datetime(self.assessed_at, "assessed_at"))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "trust_level": self.trust_level,
            "composite_score": self.composite_score,
            "evidence_sufficiency": self.evidence_sufficiency,
            "component_scores": dict(self.component_scores),
            "source_trust_assessment": dict(self.source_trust_assessment),
            "confidence_assessment": dict(self.confidence_assessment),
            "blocking_findings": [dict(item) for item in self.blocking_findings],
            "limitations": list(self.limitations),
            "warnings": list(self.warnings),
        }
        if self.assessed_at is not None:
            payload["assessed_at"] = format_utc_datetime(self.assessed_at)
        return payload
