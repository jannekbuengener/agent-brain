from __future__ import annotations

import pytest

from agent_brain.context.explanation import (
    SELF_EXPLANATION_SCHEMA,
    SelfExplanationError,
    SelfExplanationInput,
    build_self_explanation,
    supported_explanation_types,
)

from agent_brain.contracts.evidence import ClaimRef, EvidenceRef

EXPECTED_TYPES = frozenset(
    {
        "why_blocked",
        "why_risky",
        "why_stale",
        "why_decision_current",
        "why_decision_superseded",
        "why_scope_blocked",
        "why_evidence_weak",
        "why_agent_needs_go",
        "why_doc_untrusted",
    }
)


def _evidence() -> EvidenceRef:
    return EvidenceRef(
        schema_version="evidence-ref/v1",
        evidence_id="evidence-example",
        evidence_type="test-result",
        source_refs=("source-example",),
        artifact_refs=("artifact-example",),
        summary="Neutral test evidence",
    )


def _claim() -> ClaimRef:
    return ClaimRef(
        schema_version="claim-ref/v1",
        claim_id="claim-example",
        claim_type="assertion",
        statement="The neutral behavior is covered.",
        evidence_refs=("evidence-example",),
    )


def _input(**overrides) -> SelfExplanationInput:
    defaults = {
        "explanation_type": "why_blocked",
        "summary": "A blocking precondition is unresolved.",
        "reasons": ("A required input is missing.",),
        "evidence_refs": (_evidence(),),
        "required_next_step": "Provide the missing input.",
        "confidence": 0.8,
        "scope_context": "issue:example-42",
        "claim_refs": (_claim(),),
    }
    defaults.update(overrides)
    return SelfExplanationInput(**defaults)


def test_supported_explanation_types_match_portable_claire_baseline() -> None:
    assert supported_explanation_types() == EXPECTED_TYPES


@pytest.mark.parametrize("explanation_type", sorted(EXPECTED_TYPES))
def test_all_supported_types_build(explanation_type: str) -> None:
    explanation = build_self_explanation(_input(explanation_type=explanation_type))
    payload = explanation.to_dict()

    assert payload["schema_version"] == SELF_EXPLANATION_SCHEMA == "self-explanation/v1"
    assert payload["explanation_type"] == explanation_type
    assert payload["summary"]
    assert payload["reasons"]
    assert payload["required_next_step"]
    assert payload["evidence_refs"][0]["schema_version"] == "evidence-ref/v1"
    assert payload["claim_refs"][0]["schema_version"] == "claim-ref/v1"
    assert isinstance(payload["graph_path"], list)
    assert isinstance(payload["uncertainties"], list)


def test_explanation_is_deterministic_for_same_input() -> None:
    first = build_self_explanation(_input())
    second = build_self_explanation(_input())
    assert first.explanation_id == second.explanation_id
    assert first.to_dict() == second.to_dict()


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_outside_unit_interval_is_rejected(confidence: float) -> None:
    with pytest.raises(SelfExplanationError, match="confidence"):
        build_self_explanation(_input(confidence=confidence))


def test_low_confidence_adds_generic_uncertainty() -> None:
    explanation = build_self_explanation(_input(confidence=0.2, uncertainties=()))
    assert "low_confidence" in explanation.uncertainties


def test_weak_evidence_type_adds_generic_uncertainty() -> None:
    explanation = build_self_explanation(
        _input(explanation_type="why_evidence_weak", uncertainties=())
    )
    assert "weak_evidence" in explanation.uncertainties


def test_required_fields_fail_closed() -> None:
    with pytest.raises(SelfExplanationError, match="summary"):
        build_self_explanation(_input(summary=" "))
    with pytest.raises(SelfExplanationError, match="reasons"):
        build_self_explanation(_input(reasons=()))
    with pytest.raises(SelfExplanationError, match="evidence_refs"):
        build_self_explanation(_input(evidence_refs=()))
    with pytest.raises(SelfExplanationError, match="required_next_step"):
        build_self_explanation(_input(required_next_step=" "))


def test_shared_ref_types_are_required() -> None:
    with pytest.raises(TypeError, match="EvidenceRef"):
        build_self_explanation(_input(evidence_refs=({"fake": True},)))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="ClaimRef"):
        build_self_explanation(_input(claim_refs=({"fake": True},)))  # type: ignore[arg-type]


def test_guardrails_are_generic_injected_and_non_authorizing() -> None:
    explanation = build_self_explanation(_input(guardrails=("consumer_guardrail",)))
    assert "explanation_does_not_authorize_action" in explanation.guardrails
    assert "consumer_guardrail" in explanation.guardrails
    serialized = str(explanation.to_dict()).lower()
    assert "echtgeld" not in serialized
    assert "live-go" not in serialized
    assert "lr-" not in serialized


def test_explanation_exposes_no_trust_or_resolver_authority() -> None:
    payload = build_self_explanation(_input()).to_dict()
    assert "trust_classification" not in payload
    assert "resolver_status" not in payload
    assert "score" not in payload
