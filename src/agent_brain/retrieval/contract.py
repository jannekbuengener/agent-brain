"""Retrieval-Knowledge-Reasoning Contracts (Slice 7).

Produktneutrale Datentypen für Hybrid-Retrieval und deterministisches
Ranking. Keine Claire-, Trading- oder SurrealDB-Abhängigkeit. Alle Typen
sind immutable Value-Objekte mit kanonischer Serialisierung.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from agent_brain.contracts import ArtifactRef
from agent_brain.contracts.versioning import require_compatible_version

RETRIEVAL_QUERY_SCHEMA = "retrieval-query/v1"
RETRIEVAL_CANDIDATE_SCHEMA = "retrieval-candidate/v1"
RETRIEVAL_RESULT_SCHEMA = "retrieval-result/v1"
RANKING_FACTOR_SCHEMA = "ranking-factor/v1"
RANKING_EXPLANATION_SCHEMA = "ranking-explanation/v1"
RETRIEVAL_POLICY_SCHEMA = "retrieval-policy/v1"
RETRIEVAL_STOP_SCHEMA = "retrieval-stop/v1"
RETRIEVAL_IMPACT_SCHEMA = "retrieval-impact/v1"

_DEFAULT_LIMIT = 10
_MAX_LIMIT = 1000


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(item, field_name) for item in values)


def _non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must not be negative")
    return value


def _positive_int(value: int, field_name: str) -> int:
    result = _non_negative_int(value, field_name)
    if result <= 0:
        raise ValueError(f"{field_name} must be positive")
    return result


def _score(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")
    return result


def _weight(value: float, field_name: str) -> float:
    return _score(value, field_name)


def _float_tuple(values: object, field_name: str) -> tuple[float, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of numbers")
    result = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise TypeError(f"{field_name} must contain only numbers")
        result.append(float(item))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Eine produktneutrale Retrieval-Anfrage ohne Domäne-Präsuppositionen."""

    schema_version: str
    query_id: str
    query_text: str
    source_id: str
    record_type_filter: tuple[str, ...] = ()
    limit: int = _DEFAULT_LIMIT
    required_reads: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    claim_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="retrieval-query",
            supported_major=1,
        )
        object.__setattr__(self, "query_id", _required_text(self.query_id, "query_id"))
        object.__setattr__(self, "query_text", _required_text(self.query_text, "query_text"))
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        object.__setattr__(
            self,
            "record_type_filter",
            _text_tuple(self.record_type_filter, "record_type_filter"),
        )
        object.__setattr__(self, "limit", _positive_int(self.limit, "limit"))
        object.__setattr__(
            self,
            "required_reads",
            _text_tuple(self.required_reads, "required_reads"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _text_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(
            self,
            "claim_refs",
            _text_tuple(self.claim_refs, "claim_refs"),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "query_id": self.query_id,
            "query_text": self.query_text,
            "source_id": self.source_id,
            "record_type_filter": list(self.record_type_filter),
            "limit": self.limit,
        }
        if self.required_reads:
            payload["required_reads"] = list(self.required_reads)
        if self.evidence_refs:
            payload["evidence_refs"] = list(self.evidence_refs)
        if self.claim_refs:
            payload["claim_refs"] = list(self.claim_refs)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RetrievalQuery:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            schema_version=payload.get("schema_version", ""),
            query_id=payload.get("query_id", ""),
            query_text=payload.get("query_text", ""),
            source_id=payload.get("source_id", ""),
            record_type_filter=payload.get("record_type_filter", ()),
            limit=payload.get("limit", _DEFAULT_LIMIT),
            required_reads=payload.get("required_reads", ()),
            evidence_refs=payload.get("evidence_refs", ()),
            claim_refs=payload.get("claim_refs", ()),
        )


@dataclass(frozen=True, slots=True)
class RankingFactor:
    """Ein einzelner, erklärbarer Ranking-Faktor mit konservativem Default."""

    schema_version: str
    factor_name: str
    raw_value: float
    normalized_value: float
    weight: float
    contribution: float
    missing: bool = False
    fallback: bool = False

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="ranking-factor",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "factor_name",
            _required_text(self.factor_name, "factor_name"),
        )
        object.__setattr__(
            self,
            "raw_value",
            _score(self.raw_value, "raw_value"),
        )
        object.__setattr__(
            self,
            "normalized_value",
            _score(self.normalized_value, "normalized_value"),
        )
        object.__setattr__(
            self,
            "weight",
            _weight(self.weight, "weight"),
        )
        object.__setattr__(
            self,
            "contribution",
            _score(self.contribution, "contribution"),
        )
        if not isinstance(self.missing, bool):
            raise TypeError("missing must be a bool")
        if not isinstance(self.fallback, bool):
            raise TypeError("fallback must be a bool")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "factor_name": self.factor_name,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "weight": self.weight,
            "contribution": self.contribution,
            "missing": self.missing,
            "fallback": self.fallback,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RankingFactor:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            schema_version=payload.get("schema_version", ""),
            factor_name=payload.get("factor_name", ""),
            raw_value=payload.get("raw_value", 0.0),
            normalized_value=payload.get("normalized_value", 0.0),
            weight=payload.get("weight", 0.0),
            contribution=payload.get("contribution", 0.0),
            missing=payload.get("missing", False),
            fallback=payload.get("fallback", False),
        )


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    """Ein Retrieval-Kandidat mit zugeordnetem Index-Record und Faktoren."""

    schema_version: str
    candidate_id: str
    record_id: str
    artifact_ref: ArtifactRef
    score: float
    factors: tuple[RankingFactor, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="retrieval-candidate",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "candidate_id",
            _required_text(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(
            self,
            "record_id",
            _required_text(self.record_id, "record_id"),
        )
        if not isinstance(self.artifact_ref, ArtifactRef):
            raise TypeError("artifact_ref must be an ArtifactRef")
        object.__setattr__(self, "score", _score(self.score, "score"))
        if not isinstance(self.factors, (tuple, list)) or not all(
            isinstance(item, RankingFactor) for item in self.factors
        ):
            raise TypeError("factors must contain RankingFactor values")
        object.__setattr__(self, "factors", tuple(self.factors))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "record_id": self.record_id,
            "artifact_ref": self.artifact_ref.to_dict(),
            "score": self.score,
            "factors": [factor.to_dict() for factor in self.factors],
        }
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RetrievalCandidate:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        artifact_payload = payload.get("artifact_ref")
        if not isinstance(artifact_payload, Mapping):
            raise TypeError("artifact_ref must be a mapping")
        factors_raw = payload.get("factors", [])
        if isinstance(factors_raw, (str, bytes)) or not isinstance(factors_raw, list):
            raise TypeError("factors must be a list")
        factors = tuple(RankingFactor.from_dict(item) for item in factors_raw)
        return cls(
            schema_version=payload.get("schema_version", ""),
            candidate_id=payload.get("candidate_id", ""),
            record_id=payload.get("record_id", ""),
            artifact_ref=ArtifactRef.from_dict(artifact_payload),
            score=payload.get("score", 0.0),
            factors=factors,
        )


@dataclass(frozen=True, slots=True)
class RankingExplanation:
    """Strukturierte, deterministische Erklärung für einen Kandidaten."""

    schema_version: str
    candidate_id: str
    total_score: float
    factors: tuple[RankingFactor, ...]
    missing_factors: tuple[str, ...] = ()
    fallbacks: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    graph_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="ranking-explanation",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "candidate_id",
            _required_text(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(
            self,
            "total_score",
            _score(self.total_score, "total_score"),
        )
        if not isinstance(self.factors, (tuple, list)) or not all(
            isinstance(item, RankingFactor) for item in self.factors
        ):
            raise TypeError("factors must contain RankingFactor values")
        object.__setattr__(self, "factors", tuple(self.factors))
        object.__setattr__(
            self,
            "missing_factors",
            _text_tuple(self.missing_factors, "missing_factors"),
        )
        object.__setattr__(
            self,
            "fallbacks",
            _text_tuple(self.fallbacks, "fallbacks"),
        )
        object.__setattr__(
            self,
            "source_refs",
            _text_tuple(self.source_refs, "source_refs"),
        )
        object.__setattr__(
            self,
            "graph_refs",
            _text_tuple(self.graph_refs, "graph_refs"),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "total_score": self.total_score,
            "factors": [factor.to_dict() for factor in self.factors],
        }
        if self.missing_factors:
            payload["missing_factors"] = list(self.missing_factors)
        if self.fallbacks:
            payload["fallbacks"] = list(self.fallbacks)
        if self.source_refs:
            payload["source_refs"] = list(self.source_refs)
        if self.graph_refs:
            payload["graph_refs"] = list(self.graph_refs)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RankingExplanation:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        factors_raw = payload.get("factors", [])
        if isinstance(factors_raw, (str, bytes)) or not isinstance(factors_raw, list):
            raise TypeError("factors must be a list")
        factors = tuple(RankingFactor.from_dict(item) for item in factors_raw)
        return cls(
            schema_version=payload.get("schema_version", ""),
            candidate_id=payload.get("candidate_id", ""),
            total_score=payload.get("total_score", 0.0),
            factors=factors,
            missing_factors=payload.get("missing_factors", ()),
            fallbacks=payload.get("fallbacks", ()),
            source_refs=payload.get("source_refs", ()),
            graph_refs=payload.get("graph_refs", ()),
        )


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Gesamtergebnis einer Retrieval-Anfrage mit Kandidaten und Erklärungen."""

    schema_version: str
    result_id: str
    query_id: str
    candidates: tuple[RetrievalCandidate, ...]
    total_score: float
    explanation: tuple[RankingExplanation, ...]
    stop_applied: bool = False
    impact_applied: bool = False
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="retrieval-result",
            supported_major=1,
        )
        object.__setattr__(self, "result_id", _required_text(self.result_id, "result_id"))
        object.__setattr__(self, "query_id", _required_text(self.query_id, "query_id"))
        if not isinstance(self.candidates, (tuple, list)) or not all(
            isinstance(item, RetrievalCandidate) for item in self.candidates
        ):
            raise TypeError("candidates must contain RetrievalCandidate values")
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(
            self,
            "total_score",
            _score(self.total_score, "total_score"),
        )
        if not isinstance(self.explanation, (tuple, list)) or not all(
            isinstance(item, RankingExplanation) for item in self.explanation
        ):
            raise TypeError("explanation must contain RankingExplanation values")
        object.__setattr__(self, "explanation", tuple(self.explanation))
        if not isinstance(self.stop_applied, bool):
            raise TypeError("stop_applied must be a bool")
        if not isinstance(self.impact_applied, bool):
            raise TypeError("impact_applied must be a bool")
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "result_id": self.result_id,
            "query_id": self.query_id,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "total_score": self.total_score,
            "explanation": [item.to_dict() for item in self.explanation],
            "stop_applied": self.stop_applied,
            "impact_applied": self.impact_applied,
            "limitations": list(self.limitations),
        }
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RetrievalResult:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        candidates_raw = payload.get("candidates", [])
        if isinstance(candidates_raw, (str, bytes)) or not isinstance(candidates_raw, list):
            raise TypeError("candidates must be a list")
        candidates = tuple(RetrievalCandidate.from_dict(item) for item in candidates_raw)
        explanation_raw = payload.get("explanation", [])
        if isinstance(explanation_raw, (str, bytes)) or not isinstance(
            explanation_raw, list
        ):
            raise TypeError("explanation must be a list")
        explanation = tuple(RankingExplanation.from_dict(item) for item in explanation_raw)
        return cls(
            schema_version=payload.get("schema_version", ""),
            result_id=payload.get("result_id", ""),
            query_id=payload.get("query_id", ""),
            candidates=candidates,
            total_score=payload.get("total_score", 0.0),
            explanation=explanation,
            stop_applied=payload.get("stop_applied", False),
            impact_applied=payload.get("impact_applied", False),
            limitations=payload.get("limitations", ()),
        )


@dataclass(frozen=True, slots=True)
class RetrievalPolicy:
    """Injizierbare Retrieval-Politik mit Faktor-Gewichten und Tie-Break-Schlüsseln."""

    schema_version: str
    policy_id: str
    factor_weights: Mapping[str, float]
    default_factor_value: float = 0.0
    tie_break_keys: tuple[str, ...] = ()
    source_priority: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="retrieval-policy",
            supported_major=1,
        )
        object.__setattr__(self, "policy_id", _required_text(self.policy_id, "policy_id"))
        if not isinstance(self.factor_weights, Mapping):
            raise TypeError("factor_weights must be a mapping")
        weights: dict[str, float] = {}
        for key, value in self.factor_weights.items():
            key_text = _required_text(str(key), "factor_weights key")
            weights[key_text] = _weight(value, f"factor_weights[{key_text!r}]")
        total = sum(weights.values())
        if not abs(total - 1.0) < 1e-9:
            raise ValueError("factor_weights must sum to 1.0")
        object.__setattr__(
            self,
            "factor_weights",
            MappingProxyType(weights),
        )
        object.__setattr__(
            self,
            "default_factor_value",
            _score(self.default_factor_value, "default_factor_value"),
        )
        object.__setattr__(
            self,
            "tie_break_keys",
            _text_tuple(self.tie_break_keys, "tie_break_keys"),
        )
        object.__setattr__(
            self,
            "source_priority",
            _text_tuple(self.source_priority, "source_priority"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "factor_weights": dict(self.factor_weights),
            "default_factor_value": self.default_factor_value,
            "tie_break_keys": list(self.tie_break_keys),
            "source_priority": list(self.source_priority),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RetrievalPolicy:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        weights_raw = payload.get("factor_weights", {})
        if not isinstance(weights_raw, Mapping):
            raise TypeError("factor_weights must be a mapping")
        return cls(
            schema_version=payload.get("schema_version", ""),
            policy_id=payload.get("policy_id", ""),
            factor_weights=dict(weights_raw),
            default_factor_value=payload.get("default_factor_value", 0.0),
            tie_break_keys=payload.get("tie_break_keys", ()),
            source_priority=payload.get("source_priority", ()),
        )


@dataclass(frozen=True, slots=True)
class RetrievalStop:
    """Fail-closed Stop-Ergebnis einer Retrieval-Anfrage."""

    schema_version: str
    stop_id: str
    reason: str
    allowed: bool
    decision_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="retrieval-stop",
            supported_major=1,
        )
        object.__setattr__(self, "stop_id", _required_text(self.stop_id, "stop_id"))
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        if not isinstance(self.allowed, bool):
            raise TypeError("allowed must be a bool")
        object.__setattr__(
            self,
            "decision_refs",
            _text_tuple(self.decision_refs, "decision_refs"),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "stop_id": self.stop_id,
            "reason": self.reason,
            "allowed": self.allowed,
        }
        if self.decision_refs:
            payload["decision_refs"] = list(self.decision_refs)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RetrievalStop:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            schema_version=payload.get("schema_version", ""),
            stop_id=payload.get("stop_id", ""),
            reason=payload.get("reason", ""),
            allowed=payload.get("allowed", False),
            decision_refs=payload.get("decision_refs", ()),
        )


@dataclass(frozen=True, slots=True)
class RetrievalImpact:
    """Annotiertes Graph-/Struktur-Signal für einen Kandidaten."""

    schema_version: str
    impact_id: str
    candidate_id: str
    graph_distance: int
    edge_types: tuple[str, ...]
    signal_value: float

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="retrieval-impact",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "impact_id",
            _required_text(self.impact_id, "impact_id"),
        )
        object.__setattr__(
            self,
            "candidate_id",
            _required_text(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(
            self,
            "graph_distance",
            _non_negative_int(self.graph_distance, "graph_distance"),
        )
        object.__setattr__(
            self,
            "edge_types",
            _text_tuple(self.edge_types, "edge_types"),
        )
        object.__setattr__(
            self,
            "signal_value",
            _score(self.signal_value, "signal_value"),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "impact_id": self.impact_id,
            "candidate_id": self.candidate_id,
            "graph_distance": self.graph_distance,
            "edge_types": list(self.edge_types),
            "signal_value": self.signal_value,
        }
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RetrievalImpact:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            schema_version=payload.get("schema_version", ""),
            impact_id=payload.get("impact_id", ""),
            candidate_id=payload.get("candidate_id", ""),
            graph_distance=payload.get("graph_distance", 0),
            edge_types=payload.get("edge_types", ()),
            signal_value=payload.get("signal_value", 0.0),
        )
