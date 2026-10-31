"""#21 state-class classification from explicit #38 inventory facts."""

from __future__ import annotations

from agent_brain.surrealdb import (
    CANONICAL_STATE_CLASSES,
    StateClassStatus,
    classify_canonical_classes_from_table_map,
    classify_table_presence,
    issue_38_scratch_findings_2026_10_31,
)


def test_none_presence_is_unavailable_not_absent() -> None:
    finding = classify_table_presence(
        table_exists=None,
        evidence_ref="probe",
        state_class="agent_memory",
    )
    assert finding.status is StateClassStatus.UNAVAILABLE


def test_false_presence_is_absent() -> None:
    finding = classify_table_presence(
        table_exists=False,
        evidence_ref="probe",
        state_class="claim",
    )
    assert finding.status is StateClassStatus.ABSENT


def test_missing_map_key_stays_unavailable() -> None:
    findings = classify_canonical_classes_from_table_map(
        {"agent_memory": False},
        evidence_ref="partial",
    )
    by_name = {item.state_class: item for item in findings}
    assert by_name["agent_memory"].status is StateClassStatus.ABSENT
    assert by_name["claim"].status is StateClassStatus.UNAVAILABLE
    assert tuple(item.state_class for item in findings) == CANONICAL_STATE_CLASSES


def test_issue_38_scratch_findings_are_all_absent() -> None:
    findings = issue_38_scratch_findings_2026_10_31()
    assert len(findings) == len(CANONICAL_STATE_CLASSES)
    assert all(item.status is StateClassStatus.ABSENT for item in findings)
    assert all("RUNTIME_BASELINE_2026-10-31" in item.evidence_ref for item in findings)
