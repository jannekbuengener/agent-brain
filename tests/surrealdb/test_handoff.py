"""#21 state-handoff decision tests consuming #38 classifications."""

from __future__ import annotations

from agent_brain.surrealdb import (
    HandoffOutcome,
    StateClassStatus,
    VolumeAuthority,
    classify_table_presence,
    decide_state_handoff,
    issue_38_scratch_handoff_decision_2026_10_31,
)


def test_issue_38_scratch_default_is_blocked_for_unconfirmed_volume() -> None:
    decision = issue_38_scratch_handoff_decision_2026_10_31()
    assert decision.outcome is HandoffOutcome.STATE_HANDOFF_BLOCKED
    assert decision.volume_authority is VolumeAuthority.UNCONFIRMED
    assert decision.blocker_reason and "unconfirmed" in decision.blocker_reason.lower()
    assert all(item.status is StateClassStatus.ABSENT for item in decision.class_dispositions)


def test_issue_38_scratch_becomes_go_when_volume_confirmed_and_classes_absent() -> None:
    decision = issue_38_scratch_handoff_decision_2026_10_31(
        volume_authority=VolumeAuthority.CONFIRMED_PRIMARY,
    )
    assert decision.outcome is HandoffOutcome.STATE_HANDOFF_GO
    assert decision.blocker_reason is None
    assert decision.is_go


def test_unavailable_class_blocks_even_if_volume_confirmed() -> None:
    findings = (
        classify_table_presence(
            table_exists=None,
            evidence_ref="x",
            state_class="agent_memory",
        ),
        classify_table_presence(table_exists=False, evidence_ref="x", state_class="shared_memory"),
        classify_table_presence(table_exists=False, evidence_ref="x", state_class="evidence"),
        classify_table_presence(table_exists=False, evidence_ref="x", state_class="evidence_ref"),
        classify_table_presence(table_exists=False, evidence_ref="x", state_class="claim"),
        classify_table_presence(
            table_exists=False, evidence_ref="x", state_class="audit_observation"
        ),
    )
    decision = decide_state_handoff(
        findings,
        volume_authority=VolumeAuthority.CONFIRMED_PRIMARY,
        evidence_ref="test",
    )
    assert decision.outcome is HandoffOutcome.STATE_HANDOFF_BLOCKED
    assert decision.blocker_reason and "UNAVAILABLE" in decision.blocker_reason
