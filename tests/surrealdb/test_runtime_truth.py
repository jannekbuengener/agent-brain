"""Shared runtime truth + evidence-backed handoff (#67 / #21 / #38)."""

from __future__ import annotations

from agent_brain.surrealdb import (
    HandoffOutcome,
    VolumeAuthority,
    evidence_backed_handoff_2026_10_31,
    local_runtime_truth_2026_10_31,
)


def test_local_runtime_truth_marks_only_claire_surrealkv_candidate() -> None:
    truth = local_runtime_truth_2026_10_31()
    assert truth.server_version == "3.0.4"
    assert truth.configured_namespace_present is False
    assert truth.only_local_surrealkv_claire_volume is True
    assert truth.host_claire_surreal_dirs_present is False
    assert truth.volume_authority is VolumeAuthority.CONFIRMED_PRIMARY
    assert "claude-memory" in truth.alternate_surreal_volumes_checked


def test_evidence_backed_handoff_is_go_for_absent_classes() -> None:
    decision = evidence_backed_handoff_2026_10_31()
    assert decision.outcome is HandoffOutcome.STATE_HANDOFF_GO
    assert decision.is_go
    assert decision.blocker_reason is None
    assert decision.volume_authority is VolumeAuthority.CONFIRMED_PRIMARY
