from agent_brain.evidence import query_decision_history
from agent_brain.evidence.contract import DecisionQuery
from tests.evidence.conftest import decision_record, resolution_meta


def test_dangling_supersession_unresolved():
    record = decision_record(
        "decision-1",
        resolution=resolution_meta(superseded_by_ref="missing"),
    )
    result = query_decision_history(
        decisions=(record,),
        query=DecisionQuery(
            schema_version="decision-query/v1",
            mode="by_decision_id",
            decision_id="decision-1",
        ),
    )
    assert "decision-1" in result.unresolved_decision_ids
