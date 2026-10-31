from datetime import datetime

from agent_brain.contracts import ResolutionState
from agent_brain.evidence import evaluate_freshness
from agent_brain.evidence.freshness import FreshnessBundle
from tests.evidence.conftest import evidence_state, temporal


def test_not_yet_known_resolution_state():
    state = evidence_state(envelope=temporal(known_at=datetime(2026, 2, 1)))
    report = evaluate_freshness(
        bundle=FreshnessBundle(evidence_states=(state,), known_entity_ids=("evidence-1",)),
        as_of=datetime(2026, 1, 1),
    )
    entry = report.resolution_states[0]
    assert entry.resolution_state == ResolutionState.UNKNOWN
    assert entry.reason_code == "not_yet_known"
