from agent_brain.evidence import query_decision_history
from agent_brain.evidence.contract import DecisionQuery
from tests.evidence.conftest import decision_record


def test_decision_history_current_bucket():
    record = decision_record("decision-1")
    result = query_decision_history(
        decisions=(record,),
        query=DecisionQuery(
            schema_version="decision-query/v1",
            mode="by_decision_id",
            decision_id="decision-1",
        ),
        known_evidence_ids=(),
        known_claim_ids=(),
    )
    assert "decision-1" in result.current_decision_ids
