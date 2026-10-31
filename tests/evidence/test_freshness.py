from datetime import datetime
from agent_brain.evidence import evaluate_freshness
from agent_brain.evidence.freshness import FreshnessBundle
from tests.evidence.conftest import evidence_state, temporal

def test_validity_window_closed_stale_type():
    state = evidence_state(envelope=temporal(valid_until=datetime(2026, 1, 1)))
    report = evaluate_freshness(
        bundle=FreshnessBundle(evidence_states=(state,), known_entity_ids=("evidence-1",)),
        as_of=datetime(2026, 2, 1),
    )
    assert any(item.stale_type == "validity_window_closed" for item in report.stale_findings)
