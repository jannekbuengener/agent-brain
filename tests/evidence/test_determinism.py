from agent_brain.evidence import resolve_evidence
from tests.evidence.conftest import evidence_ref, evidence_state

def test_resolve_evidence_reorder_invariant():
    refs = (evidence_ref("b"), evidence_ref("a"))
    states = (evidence_state("a"), evidence_state("b"))
    one = resolve_evidence(evidence=refs, states=states)
    two = resolve_evidence(evidence=tuple(reversed(refs)), states=tuple(reversed(states)))
    assert one.matched_evidence_ids == two.matched_evidence_ids
