from agent_brain import contracts
from agent_brain.contracts.registry import CONTRACT_SCHEMAS

EXPECTED_SCHEMAS = {
    "repository-source": "repository-source/v1",
    "repository-profile": "repository-profile/v1",
    "artifact-ref": "artifact-ref/v1",
    "index-record": "index-record/v1",
    "graph-edge": "graph-edge/v1",
    "evidence-ref": "evidence-ref/v1",
    "claim-ref": "claim-ref/v1",
    "temporal-envelope": "temporal-envelope/v1",
    "provenance": "provenance/v1",
    "resolution-meta": "resolution-meta/v1",
}


def test_contract_registry_contains_all_shared_contract_families() -> None:
    assert dict(CONTRACT_SCHEMAS) == EXPECTED_SCHEMAS


def test_contract_registry_versions_match_their_family_names() -> None:
    for family, version in CONTRACT_SCHEMAS.items():
        assert version == f"{family}/v1"


def test_contract_package_exports_memory_hardening_types() -> None:
    assert contracts.TemporalEnvelope.__name__ == "TemporalEnvelope"
    assert contracts.Provenance.__name__ == "Provenance"
    assert contracts.SourceSpan.__name__ == "SourceSpan"
    assert contracts.ResolutionMeta.__name__ == "ResolutionMeta"
    assert contracts.ResolutionState.__name__ == "ResolutionState"
