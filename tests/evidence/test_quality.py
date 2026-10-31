from datetime import datetime

from agent_brain.evidence import score_quality


def test_quality_missing_dimension_limitation():
    result = score_quality(scope_id="scope", as_of=datetime(2026, 1, 1))
    assert any("missing_dimension" in item for item in result.limitations)
