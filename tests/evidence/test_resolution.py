from agent_brain.evidence import resolve_claims, resolve_evidence
from tests.evidence.conftest import claim_ref, claim_state

def test_resolve_claims_missing_evidence():
    claim = claim_ref("claim-1", ("missing-evidence",))
    result = resolve_claims(claims=(claim,), states=(claim_state(),), evidence=())
    assert "claim-1" in result.missing_evidence_claim_ids

def test_resolve_evidence_no_as_of_parameter():
    assert "as_of" not in resolve_evidence.__code__.co_varnames
