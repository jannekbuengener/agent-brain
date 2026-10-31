"""Provenance gate for Memory Read (#11)."""

from __future__ import annotations

from agent_brain.contracts.resolution import ResolutionState
from agent_brain.memory.read import evaluate_provenance_gate
from tests.memory.helpers_read import make_entry


def test_complete_provenance_passes() -> None:
    entry = make_entry()
    result = evaluate_provenance_gate(entry)
    assert result.passed is True
    assert result.forced_state is None


def test_missing_evidence_and_lineage_fails_unknown() -> None:
    entry = make_entry(evidence_refs=())
    result = evaluate_provenance_gate(entry)
    assert result.passed is False
    assert result.forced_state is ResolutionState.UNKNOWN
    assert "missing_evidence_or_lineage" in result.reason_codes


def test_missing_confidence_is_visible_not_trusted() -> None:
    entry = make_entry(confidence=None, source_trust=None)
    result = evaluate_provenance_gate(entry)
    assert result.passed is True
    assert "missing_confidence" in result.reason_codes
    assert "missing_source_trust" in result.reason_codes
