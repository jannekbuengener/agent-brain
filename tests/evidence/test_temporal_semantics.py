from datetime import datetime
from agent_brain.evidence import evaluate_freshness
from agent_brain.evidence.freshness import FreshnessBundle
from tests.evidence.conftest import evidence_state, temporal

def test_system_as_of_does_not_force_stale():
    state = evidence_state(
        envelope=temporal(system_as_of=datetime(2020, 1, 1), known_at=datetime(2026, 1, 1))
    )
    report = evaluate_freshness(
        bundle=FreshnessBundle(evidence_states=(state,), known_entity_ids=("evidence-1",)),
        as_of=datetime(2026, 6, 1),
    )
    assert report.system_as_of is not None
