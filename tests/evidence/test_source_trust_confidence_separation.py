"""source_trust and confidence must remain independent (#8 AC5)."""

from __future__ import annotations

from agent_brain.evidence import build_trust_summary, resolve_evidence
from agent_brain.evidence.contract import TrustRequest
from tests.evidence.conftest import evidence_ref, evidence_state, resolution_meta


def test_trust_summary_has_separate_assessments() -> None:
    summary = build_trust_summary(
        request=TrustRequest(schema_version="trust-request/v1", scope="scope"),
    )
    assert "evaluated_count" in summary.source_trust_assessment
    assert "evaluated_count" in summary.confidence_assessment


def test_changing_source_trust_does_not_change_confidence_assessment() -> None:
    refs = (evidence_ref("evidence-1"),)
    high_trust = resolve_evidence(
        evidence=refs,
        states=(
            evidence_state(
                resolution=resolution_meta(source_trust=0.9, confidence=0.4),
            ),
        ),
    )
    low_trust = resolve_evidence(
        evidence=refs,
        states=(
            evidence_state(
                resolution=resolution_meta(source_trust=0.1, confidence=0.4),
            ),
        ),
    )
    request = TrustRequest(schema_version="trust-request/v1", scope="scope")
    high = build_trust_summary(request=request, evidence_resolution=high_trust)
    low = build_trust_summary(request=request, evidence_resolution=low_trust)
    assert high.confidence_assessment == low.confidence_assessment
    assert high.source_trust_assessment != low.source_trust_assessment
    # Neither assessment contributes to composite_score as a collapsed blend.
    assert high.composite_score == low.composite_score
