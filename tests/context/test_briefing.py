from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_brain.context.briefing import (
    BRIEFING_SCHEMA,
    BriefingError,
    BriefingRequest,
    build_briefing,
)

from agent_brain.context.package import ContextArtifact, ContextPackageRequest, build_context_package
from agent_brain.context.required_reads import RequiredRead
from agent_brain.context.validation import ValidationPlanInput, build_validation_plan
from agent_brain.contracts.evidence import EvidenceRef
from agent_brain.contracts.repository import ArtifactRef
from agent_brain.core.policy import PolicyDecision
from agent_brain.core.source_priority import SourcePriority

FIXTURE = Path("tests/fixtures/context/briefing.neutral.v1.json")


class _PolicyHook:
    def __init__(self, decision: PolicyDecision) -> None:
        self.decision = decision
        self.seen_operation: str | None = None

    def evaluate(self, context):
        self.seen_operation = context.operation
        return self.decision


def _request(**overrides) -> BriefingRequest:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))["request"]
    payload.update(overrides)
    return BriefingRequest(
        task_id=payload["task_id"],
        task_scope=payload["task_scope"],
        target_issue=payload["target_issue"],
        requested_depth=payload["requested_depth"],
        operation_mode=payload["operation_mode"],
        target_paths=tuple(payload["target_paths"]),
        target_symbols=tuple(payload["target_symbols"]),
        target_concepts=tuple(payload["target_concepts"]),
        risk_level=payload["risk_level"],
    )


def _evidence() -> EvidenceRef:
    return EvidenceRef(
        schema_version="evidence-ref/v1",
        evidence_id="evidence-example",
        evidence_type="test-result",
        source_refs=("source-example",),
        artifact_refs=("artifact-example",),
        summary="Neutral briefing evidence",
    )


def _package():
    artifact = ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id="artifact-example",
        source_id="source-example",
        source_path="src/widget.py",
        source_hash="a" * 64,
    )
    return build_context_package(
        ContextPackageRequest(
            target_scope="issue:example-42",
            artifacts=(ContextArtifact(ref=artifact, artifact_type="source"),),
            source_priority=SourcePriority(("repository_live",)),
            generated_at_or_as_of="2026-10-20T20:00:00",
        )
    )


def _validation():
    return build_validation_plan(
        ValidationPlanInput(
            impact_id="impact-example",
            required_checks=("contract_test",),
            stop_conditions=("stop_on_unexpected_change",),
        )
    )


def test_briefing_is_deterministic_and_carries_shared_context() -> None:
    reads = (
        RequiredRead(
            path="AGENTS.md",
            priority="critical",
            reason="Read repository instructions first.",
            available=True,
        ),
    )
    kwargs = {
        "context_package": _package(),
        "required_reads": reads,
        "evidence_refs": (_evidence(),),
        "validation_plan": _validation(),
        "guardrails": ("consumer_guardrail",),
        "stop_conditions": ("stop_if_scope_changes",),
        "unresolved_questions": ("Is the consumer updated?",),
    }
    first = build_briefing(_request(), **kwargs)
    second = build_briefing(_request(), **kwargs)
    payload = first.to_dict()

    assert first.briefing_id == second.briefing_id
    assert payload == second.to_dict()
    assert payload["schema_version"] == BRIEFING_SCHEMA == "agent-briefing/v1"
    assert "Review the neutral widget contract." in payload["scope_summary"]
    assert payload["context_package_ref"] == _package().package_id
    assert payload["required_reads"][0]["path"] == "AGENTS.md"
    assert payload["relevant_evidence"][0]["schema_version"] == "evidence-ref/v1"
    assert payload["validation_plan"]["schema_version"] == "validation-plan/v1"
    assert "consumer_guardrail" in payload["guardrails"]
    assert "stop_if_scope_changes" in payload["stop_conditions"]
    assert payload["unresolved_questions"] == ["Is the consumer updated?"]


@pytest.mark.parametrize("depth", ["", "full", " QUICK "])
def test_requested_depth_is_fail_closed(depth: str) -> None:
    with pytest.raises(BriefingError, match="requested_depth"):
        build_briefing(_request(requested_depth=depth), context_package=None)


def test_absent_policy_hook_grants_no_extra_authority() -> None:
    briefing = build_briefing(
        _request(),
        context_package=None,
        guardrails=("consumer_guardrail",),
    )
    assert briefing.human_go_required is False
    assert "briefing_does_not_authorize_action" in briefing.guardrails
    assert "consumer_guardrail" in briefing.guardrails


def test_policy_denial_requires_human_go_and_adds_stop_reasons() -> None:
    hook = _PolicyHook(PolicyDecision(allowed=False, reasons=("approval_required", "scope_unclear")))
    briefing = build_briefing(
        _request(),
        context_package=None,
        guardrails=("consumer_guardrail",),
        policy_hook=hook,
    )
    assert hook.seen_operation == "build_briefing"
    assert briefing.human_go_required is True
    assert "approval_required" in briefing.stop_conditions
    assert "scope_unclear" in briefing.stop_conditions
    assert "consumer_guardrail" in briefing.guardrails


def test_policy_allow_does_not_erase_caller_guardrails() -> None:
    hook = _PolicyHook(PolicyDecision(allowed=True))
    briefing = build_briefing(
        _request(),
        context_package=None,
        guardrails=("consumer_guardrail",),
        stop_conditions=("caller_stop",),
        policy_hook=hook,
    )
    assert briefing.human_go_required is False
    assert briefing.guardrails == (
        "briefing_does_not_authorize_action",
        "consumer_guardrail",
    )
    assert briefing.stop_conditions == ("caller_stop",)


def test_manual_review_in_validation_requires_human_go() -> None:
    validation = build_validation_plan(
        ValidationPlanInput(impact_id="impact-example", manual_review_needed=True)
    )
    briefing = build_briefing(_request(), context_package=None, validation_plan=validation)
    assert briefing.human_go_required is True
    assert "manual_review_required" in briefing.stop_conditions


def test_briefing_has_no_product_specific_authority() -> None:
    payload = str(build_briefing(_request(), context_package=None).to_dict()).lower()
    for forbidden in ("echtgeld", "live-go", "lr-", "trading", "surrealdb-local"):
        assert forbidden not in payload
