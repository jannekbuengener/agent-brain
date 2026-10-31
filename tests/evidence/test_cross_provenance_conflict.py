"""Cross-provenance conflicts stay explicit — no silent last-write-wins."""

from __future__ import annotations

from datetime import datetime

from agent_brain.evidence import detect_contradictions, resolve_evidence
from agent_brain.evidence.contradiction import ContradictionBundle
from tests.evidence.conftest import evidence_ref, evidence_state


def test_cross_provenance_conflict_group() -> None:
    refs = (evidence_ref("evidence-1"),)
    states = (
        evidence_state("evidence-1", source_ref="source-a", source_hash="a" * 64),
        evidence_state("evidence-1", source_ref="source-b", source_hash="b" * 64),
    )
    result = resolve_evidence(evidence=refs, states=states)
    assert result.conflicting_evidence_ids
    # No winner field / no silent collapse to a single state.
    assert not hasattr(result, "winning_evidence_id")
    assert "evidence-1" in {
        eid for group in result.conflicting_evidence_ids for eid in group
    } or any("evidence-1" in str(group) for group in result.conflicting_evidence_ids)


def test_cross_provenance_conflict_materialized_as_blocking_finding() -> None:
    refs = (evidence_ref("evidence-1"),)
    states = (
        evidence_state("evidence-1", source_ref="source-a", source_hash="a" * 64),
        evidence_state("evidence-1", source_ref="source-b", source_hash="b" * 64),
    )
    resolution = resolve_evidence(evidence=refs, states=states)
    scan = detect_contradictions(
        bundle=ContradictionBundle(
            evidence_refs=refs,
            evidence_states=states,
            evidence_resolution=resolution,
        ),
        as_of=datetime(2026, 2, 1),
    )
    assert any(
        finding.rule_type == "cross_provenance_conflict" for finding in scan.findings
    )
    assert scan.blocking_count >= 1
