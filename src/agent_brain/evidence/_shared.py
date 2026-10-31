"""Shared validators and vocabularies for slice 8."""

from __future__ import annotations

import math

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


def required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return required_text(value, field_name)


def text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(required_text(item, field_name) for item in values)


def score(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{field_name} must be a finite number between 0.0 and 1.0")
    return result


def validate_vocab(value: str, field_name: str, vocabulary: tuple[str, ...]) -> str:
    normalized = required_text(value, field_name)
    if normalized not in vocabulary:
        raise ValueError(f"{field_name} must be one of {vocabulary}")
    return normalized
