from __future__ import annotations

import pytest

from agent_brain.distribution import (
    ChangeKind,
    CompatibilityReport,
    CompatibilityVerdict,
    build_rollback_plan,
    build_upgrade_plan,
    classify_surface_diff,
)


def test_upgrade_plan_is_ordered_and_pins_exact_versions() -> None:
    compatibility = classify_surface_diff(removed=set(), added={"agent_brain:__version__"})
    plan = build_upgrade_plan(
        current_version="0.1.0",
        target_version="0.1.1",
        compatibility=compatibility,
    )

    assert plan.current_version == "0.1.0"
    assert plan.target_version == "0.1.1"
    assert plan.target_requirement == "agent-brain==0.1.1"
    assert [step.name for step in plan.steps] == [
        "identify_current",
        "identify_target",
        "compatibility_check",
        "upgrade_install",
        "consumer_smoke",
        "record_success",
    ]


def test_upgrade_plan_refuses_incompatible_target() -> None:
    incompatible = CompatibilityReport(
        verdict=CompatibilityVerdict.INCOMPATIBLE,
        kind=ChangeKind.BREAKING,
        removed=frozenset({"agent_brain.distribution:PinSpec"}),
    )
    with pytest.raises(ValueError, match="incompatible"):
        build_upgrade_plan(
            current_version="0.1.0",
            target_version="1.0.0",
            compatibility=incompatible,
        )


def test_rollback_plan_reinstalls_previous_exact_pin() -> None:
    plan = build_rollback_plan(failed_version="0.1.1", previous_version="0.1.0")

    assert plan.previous_requirement == "agent-brain==0.1.0"
    assert [step.name for step in plan.steps] == [
        "remember_previous",
        "acknowledge_failure",
        "reinstall_previous",
        "consumer_smoke",
        "record_rollback",
    ]
    assert plan.steps[2].requirement == "agent-brain==0.1.0"
