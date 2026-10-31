from agent_brain.evidence import build_trust_summary
from agent_brain.evidence.contract import TrustRequest

def test_empty_inputs_not_strong():
    summary = build_trust_summary(
        request=TrustRequest(schema_version="trust-request/v1", scope="scope"),
    )
    assert summary.trust_level != "strong"
