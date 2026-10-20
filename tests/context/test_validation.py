from __future__ import annotations

from agent_brain.context.validation import (
    VALIDATION_PLAN_SCHEMA,
    ValidationPlanError,
    ValidationPlanInput,
    build_validation_plan,
)


def _input(**overrides) -> ValidationPlanInput:
    defaults = {
        "impact_id": "impact-example",
        "impact_level": "medium",
        "confidence": "high",
        "required_checks": ("contract_test",),
        "suggested_tests": ("pytest tests/context",),
        "docs_to_review": ("docs/context/README.md",),
        "evidence_to_collect": ("ci_result",),
        "commands_to_consider": ("python -m pytest -q",),
        "blocking_preconditions": ("baseline_known",),
        "stop_conditions": ("unexpected_scope_change",),
        "manual_review_needed": False,
    }
    defaults.update(overrides)
    return ValidationPlanInput(**defaults)


def test_validation_plan_is_deterministic_and_serializable() -> None:
    first = build_validation_plan(_input())
    second = build_validation_plan(_input())

    assert first.plan_id == second.plan_id
    assert first.to_dict() == second.to_dict()
    assert first.to_dict()["schema_version"] == VALIDATION_PLAN_SCHEMA == "validation-plan/v1"
    assert first.to_dict()["required_checks"] == ["contract_test"]
    assert first.to_dict()["commands_to_consider"] == ["python -m pytest -q"]
    assert "commands_to_execute" not in first.to_dict()


def test_blocking_and_stop_conditions_are_preserved() -> None:
    plan = build_validation_plan(_input())
    assert plan.blocking_preconditions == ("baseline_known",)
    assert plan.stop_conditions == ("unexpected_scope_change",)


def test_manual_review_is_fail_closed_without_authorizing_action() -> None:
    plan = build_validation_plan(
        _input(
            manual_review_needed=True,
            blocking_preconditions=(),
            stop_conditions=(),
        )
    )
    assert "manual_review_required" in plan.blocking_preconditions
    assert "manual_review_required" in plan.stop_conditions
    assert plan.manual_review_needed is True


def test_blank_impact_id_fails_closed() -> None:
    try:
        build_validation_plan(_input(impact_id=" "))
    except ValidationPlanError as exc:
        assert "impact_id" in str(exc)
    else:
        raise AssertionError("blank impact_id must fail closed")


def test_product_specific_claire_derivations_are_absent() -> None:
    payload = str(build_validation_plan(_input()).to_dict()).lower()
    for forbidden in ("governance_touched", "echtgeld", "live-go", "lr-", "trading"):
        assert forbidden not in payload
