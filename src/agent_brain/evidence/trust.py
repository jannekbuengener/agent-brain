"""Trust summary assessment."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from agent_brain.evidence.contract import (
    TRUST_SUMMARY_SCHEMA,
    ClaimResolution,
    ContradictionScanResult,
    DecisionHistoryResult,
    EvidenceResolution,
    FreshnessReport,
    QualityAssessment,
    ScopeDriftReport,
    TrustError,
    TrustPolicy,
    TrustRequest,
    TrustSummary,
    compute_weighted_mean,
)

_DEFAULT_LIMITATIONS = (
    "Trust summary is assessment-only; it does not grant authorization.",
)


def _component_score_evidence(resolution: EvidenceResolution | None) -> float | None:
    if resolution is None:
        return None
    total = len(resolution.matched_evidence_ids)
    if total == 0:
        return 0.0
    moderate = len(resolution.by_strength.get("moderate", ()))
    strong = len(resolution.by_strength.get("strong", ()))
    return (moderate + strong) / total


def _component_score_claims(resolution: ClaimResolution | None) -> float | None:
    if resolution is None:
        return None
    total = len(resolution.matched_claim_ids)
    if total == 0:
        return 0.0
    blocked = len(resolution.disputed_claim_ids) + len(resolution.invalidated_claim_ids)
    return max(0.0, 1.0 - (blocked / total))


def _component_score_decisions(history: DecisionHistoryResult | None) -> float | None:
    if history is None:
        return None
    total = (
        len(history.current_decision_ids)
        + len(history.superseded_decision_ids)
        + len(history.invalidated_decision_ids)
        + len(history.unresolved_decision_ids)
    )
    if total == 0:
        return 0.0
    return len(history.current_decision_ids) / total


def _collect_trust_values(
    evidence_resolution: EvidenceResolution | None,
    claim_resolution: ClaimResolution | None,
    decision_history: DecisionHistoryResult | None,
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    source_trust_values: list[float] = []
    confidence_values: list[float] = []
    # Trust/confidence are reported separately and do not affect composite score.
    return (
        MappingProxyType(
            {
                "evaluated_count": len(source_trust_values),
                "not_evaluated_count": 0,
            }
        ),
        MappingProxyType(
            {
                "evaluated_count": len(confidence_values),
                "not_evaluated_count": 0,
            }
        ),
    )


def build_trust_summary(
    *,
    request: TrustRequest,
    evidence_resolution: EvidenceResolution | None = None,
    claim_resolution: ClaimResolution | None = None,
    decision_history: DecisionHistoryResult | None = None,
    contradictions: ContradictionScanResult | None = None,
    freshness: FreshnessReport | None = None,
    scope_drift: ScopeDriftReport | None = None,
    quality: QualityAssessment | None = None,
    policy: TrustPolicy | None = None,
) -> TrustSummary:
    if not isinstance(request, TrustRequest):
        raise TrustError("request must be a TrustRequest")
    if policy is None:
        policy = TrustPolicy.default()

    limitations = list(_DEFAULT_LIMITATIONS)
    component_scores: dict[str, float | None] = {
        "evidence": _component_score_evidence(evidence_resolution),
        "claims": _component_score_claims(claim_resolution),
        "decisions": _component_score_decisions(decision_history),
    }
    missing_required = [
        name for name in policy.required_components if component_scores.get(name) is None
    ]
    if missing_required:
        limitations.append(f"required_component_missing:{','.join(missing_required)}")

    weighted_pairs: list[tuple[float, float]] = []
    for name, value in component_scores.items():
        if value is None:
            continue
        weighted_pairs.append((value, policy.component_weights.get(name, 0.0)))
    composite = compute_weighted_mean(tuple(weighted_pairs))

    blocking_findings: list[Mapping[str, object]] = []
    if contradictions is not None:
        blocking_findings.extend(
            {"source": "contradiction", "finding_id": item.finding_id, "severity": item.severity}
            for item in contradictions.findings
            if item.severity == "blocking"
        )
    if freshness is not None:
        blocking_findings.extend(
            {"source": "freshness", "finding_id": item.finding_id, "severity": item.severity}
            for item in freshness.stale_findings
            if item.severity == "blocking"
        )
    if scope_drift is not None:
        blocking_findings.extend(
            {"source": "scope_drift", "finding_id": item.finding_id, "severity": item.severity}
            for item in scope_drift.findings
            if item.severity == "blocking"
        )
    if claim_resolution is not None:
        for claim_id in claim_resolution.missing_evidence_claim_ids:
            blocking_findings.append(
                {"source": "claims", "claim_id": claim_id, "severity": "blocking"}
            )

    trust_level = "insufficient"
    if blocking_findings:
        trust_level = "insufficient"
    elif composite is None:
        trust_level = "insufficient"
    elif composite >= policy.level_thresholds["strong"] and not missing_required:
        trust_level = "strong"
    elif composite >= policy.level_thresholds["partial"]:
        trust_level = "partial"
    else:
        trust_level = "partial" if not missing_required else "partial"
    if missing_required and trust_level == "strong":
        trust_level = "partial"
    if missing_required and composite is None:
        trust_level = "insufficient"

    evidence_sufficiency = "insufficient"
    if evidence_resolution is None:
        evidence_sufficiency = "insufficient"
    elif evidence_resolution.matched_evidence_ids:
        strong = len(evidence_resolution.by_strength.get("strong", ()))
        if strong == len(evidence_resolution.matched_evidence_ids):
            evidence_sufficiency = "sufficient"
        elif strong > 0:
            evidence_sufficiency = "partial"
        else:
            evidence_sufficiency = "partial"

    source_trust_assessment, confidence_assessment = _collect_trust_values(
        evidence_resolution,
        claim_resolution,
        decision_history,
    )
    assessed_at = quality.scored_at if quality is not None else None

    return TrustSummary(
        schema_version=TRUST_SUMMARY_SCHEMA,
        trust_level=trust_level,
        composite_score=composite,
        evidence_sufficiency=evidence_sufficiency,
        component_scores=MappingProxyType(component_scores),
        source_trust_assessment=source_trust_assessment,
        confidence_assessment=confidence_assessment,
        blocking_findings=tuple(blocking_findings),
        limitations=tuple(limitations),
        assessed_at=assessed_at,
        warnings=(),
    )
