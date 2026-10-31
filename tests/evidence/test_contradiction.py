from datetime import datetime
from agent_brain.evidence import detect_contradictions
from agent_brain.evidence.contradiction import ContradictionBundle, default_contradiction_rule_set

def test_contradiction_default_rules_present():
    assert default_contradiction_rule_set().rules
    result = detect_contradictions(
        bundle=ContradictionBundle(),
        as_of=datetime(2026, 1, 1, 0, 0, 0),
    )
    assert result.limitations
