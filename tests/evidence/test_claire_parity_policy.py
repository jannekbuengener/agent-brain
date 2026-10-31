import json
from pathlib import Path
from agent_brain.evidence.contract import QualityPolicy, TrustPolicy

def test_claire_parity_policy_fixture_values():
    path = Path("tests/fixtures/evidence/claire_parity_policy.v1.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    q = data["quality_policy"]
    assert q["grade_bands"]["blocking"] == 0.30
    assert QualityPolicy.default().grade_bands["blocking"] == q["grade_bands"]["blocking"]
    assert TrustPolicy.default().level_thresholds["strong"] == data["trust_policy"]["level_thresholds"]["strong"]
