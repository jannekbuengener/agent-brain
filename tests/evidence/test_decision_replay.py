from datetime import datetime
from agent_brain.evidence import build_decision_replay
from agent_brain.evidence.contract import DecisionReplayQuery
from tests.evidence.conftest import decision_record

def test_decision_replay_authorization_implied_false():
    replay = build_decision_replay(
        decisions=(decision_record(),),
        query=DecisionReplayQuery(
            schema_version="decision-replay-query/v1",
            decision_id="decision-1",
        ),
        as_of=datetime(2026, 1, 20, 0, 0, 0),
    )
    assert replay.authorization_implied is False
    assert replay.limitations
