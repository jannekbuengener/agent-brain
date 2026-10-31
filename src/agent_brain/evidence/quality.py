"""Quality assessment over stage 1-3 results."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime

from agent_brain.contracts import GraphEdge
from agent_brain.evidence.contract import (
    QUALITY_ASSESSMENT_SCHEMA,
    QUALITY_DIMENSION_SCORE_SCHEMA,
    ClaimResolution,
    ContradictionScanResult,
    DecisionHistoryResult,
    EvidenceResolution,
    FreshnessReport,
    QualityAssessment,
    QualityDimensionScore,
    QualityError,
    QualityPolicy,
    ScopeDriftReport,
    SurfaceState,
    compute_weighted_mean,
)

_DEFAULT_LIMITATIONS = (
    "Quality assessment is informational; it does not grant authorization.",
)


def _grade_for_score(score: float, policy: QualityPolicy) -> str:
    bands = policy.grade_bands
    if score < bands["blocking"]:
        return "blocking"
    if score < bands["watch"]:
        return "watch"
    if score < bands["weak"]:
        return "weak"
    return "good"


def _penalty_score(findings, policy: QualityPolicy, warnings: list[str], type_field: str) -> float:
    penalty = 0.0
    for finding in findings:
        status = getattr(finding, "status", "open")
        if status in policy.finding_exempt_statuses:
            continue
        if status not in {"open", "resolved", "refreshed", "replaced"}:
            warnings.append("unknown_finding_status")
        rule_type = getattr(finding, type_field, None)
        if rule_type is not None and rule_type not in {
            *(getattr(finding, "rule_type", None),),
        }:
            pass
        severity = getattr(finding, "severity", "info")
        penalty += policy.severity_penalties.get(severity, 0.0)
    return max(0.0, 1.0 - penalty)


def score_quality(
    *,
    scope_id: str,
    as_of: datetime,
    level: str = "system",
    surfaces: Sequence[SurfaceState] = (),
    dependency_edges: Sequence[GraphEdge] = (),
    evidence_resolution: EvidenceResolution | None = None,
    claim_resolution: ClaimResolution | None = None,
    decision_history: DecisionHistoryResult | None = None,
    contradictions: ContradictionScanResult | None = None,
    freshness: FreshnessReport | None = None,
    scope_drift: ScopeDriftReport | None = None,
    policy: QualityPolicy | None = None,
) -> QualityAssessment:
    if not isinstance(as_of, datetime):
        raise QualityError("as_of must be a datetime")
    if policy is None:
        policy = QualityPolicy.default()
    warnings: list[str] = []
    limitations = list(_DEFAULT_LIMITATIONS)
    dimensions: list[QualityDimensionScore] = []

    if evidence_resolution is not None:
        total = len(evidence_resolution.matched_evidence_ids)
        strong = len(evidence_resolution.by_strength.get("strong", ()))
        score = (strong / total) if total else 0.0
        dimensions.append(
            QualityDimensionScore(
                schema_version=QUALITY_DIMENSION_SCORE_SCHEMA,
                dimension="evidence",
                score=score,
                grade=_grade_for_score(score, policy),
                explanation="Evidence strength coverage.",
                inputs_used=total,
            )
        )
    else:
        limitations.append("missing_dimension:evidence")

    if claim_resolution is not None:
        total = len(claim_resolution.matched_claim_ids)
        ok = total - len(claim_resolution.missing_evidence_claim_ids)
        score = (ok / total) if total else 0.0
        dimensions.append(
            QualityDimensionScore(
                schema_version=QUALITY_DIMENSION_SCORE_SCHEMA,
                dimension="coverage",
                score=score,
                grade=_grade_for_score(score, policy),
                explanation="Claim coverage with resolvable evidence.",
                inputs_used=total,
            )
        )
    else:
        limitations.append("missing_dimension:coverage")

    if decision_history is not None:
        total = (
            len(decision_history.current_decision_ids)
            + len(decision_history.superseded_decision_ids)
            + len(decision_history.invalidated_decision_ids)
            + len(decision_history.unresolved_decision_ids)
        )
        current = len(decision_history.current_decision_ids)
        score = (current / total) if total else 0.0
        dimensions.append(
            QualityDimensionScore(
                schema_version=QUALITY_DIMENSION_SCORE_SCHEMA,
                dimension="decision_validity",
                score=score,
                grade=_grade_for_score(score, policy),
                explanation="Decision validity ratio.",
                inputs_used=total,
            )
        )
    else:
        limitations.append("missing_dimension:decision_validity")

    if dependency_edges:
        total = len(dependency_edges)
        confident = sum(
            1
            for edge in dependency_edges
            if edge.confidence >= policy.dependency_confidence_threshold
        )
        score = confident / total if total else 0.0
        dimensions.append(
            QualityDimensionScore(
                schema_version=QUALITY_DIMENSION_SCORE_SCHEMA,
                dimension="dependency_confidence",
                score=score,
                grade=_grade_for_score(score, policy),
                explanation="Dependency edge confidence threshold coverage.",
                inputs_used=total,
            )
        )
    else:
        limitations.append("missing_dimension:dependency_confidence")

    if contradictions is not None:
        score = _penalty_score(contradictions.findings, policy, warnings, "rule_type")
        dimensions.append(
            QualityDimensionScore(
                schema_version=QUALITY_DIMENSION_SCORE_SCHEMA,
                dimension="contradiction",
                score=score,
                grade=_grade_for_score(score, policy),
                explanation="Inverse penalty from contradiction findings.",
                inputs_used=len(contradictions.findings),
            )
        )
    else:
        limitations.append("missing_dimension:contradiction")

    if freshness is not None:
        score = _penalty_score(freshness.stale_findings, policy, warnings, "stale_type")
        dimensions.append(
            QualityDimensionScore(
                schema_version=QUALITY_DIMENSION_SCORE_SCHEMA,
                dimension="freshness",
                score=score,
                grade=_grade_for_score(score, policy),
                explanation="Inverse penalty from stale findings.",
                inputs_used=len(freshness.stale_findings),
            )
        )
    else:
        limitations.append("missing_dimension:freshness")

    if scope_drift is not None:
        score = _penalty_score(scope_drift.findings, policy, warnings, "drift_type")
        dimensions.append(
            QualityDimensionScore(
                schema_version=QUALITY_DIMENSION_SCORE_SCHEMA,
                dimension="scope_risk",
                score=score,
                grade=_grade_for_score(score, policy),
                explanation="Inverse penalty from scope drift findings.",
                inputs_used=len(scope_drift.findings),
            )
        )
    else:
        limitations.append("missing_dimension:scope_risk")

    weighted_pairs: list[tuple[float, float]] = []
    for dimension in dimensions:
        if not math.isfinite(dimension.score):
            warnings.append("non_finite_score")
            continue
        weight = policy.dimension_weights.get(dimension.dimension, 0.0)
        weighted_pairs.append((dimension.score, weight))
    overall = compute_weighted_mean(tuple(weighted_pairs))
    overall_score = overall if overall is not None else 0.0
    overall_grade = _grade_for_score(overall_score, policy)
    if any(item.grade == "blocking" for item in dimensions) and overall_grade in {"weak", "good"}:
        overall_grade = "watch"

    return QualityAssessment(
        schema_version=QUALITY_ASSESSMENT_SCHEMA,
        scope_id=scope_id,
        level=level,
        scored_at=as_of,
        overall_score=overall_score,
        overall_grade=overall_grade,
        dimensions=tuple(dimensions),
        limitations=tuple(limitations),
        warnings=tuple(sorted(set(warnings))),
    )
