from agent_brain.evidence import build_trust_summary
from agent_brain.evidence.contract import TrustRequest

FORBIDDEN = {"approved", "go_token", "trading_allowed"}

def test_trust_summary_forbidden_fields():
    summary = build_trust_summary(
        request=TrustRequest(schema_version="trust-request/v1", scope="scope"),
    )
    payload = summary.to_dict()
    assert not FORBIDDEN.intersection(payload.keys())
    assert summary.limitations
