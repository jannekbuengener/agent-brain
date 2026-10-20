from agent_brain.contracts.registry import CONTRACT_SCHEMAS

EXPECTED_SCHEMAS = {
    "repository-source": "repository-source/v1",
    "repository-profile": "repository-profile/v1",
    "artifact-ref": "artifact-ref/v1",
    "index-record": "index-record/v1",
    "graph-edge": "graph-edge/v1",
    "evidence-ref": "evidence-ref/v1",
    "claim-ref": "claim-ref/v1",
}


def test_contract_registry_contains_all_shared_contract_families() -> None:
    assert dict(CONTRACT_SCHEMAS) == EXPECTED_SCHEMAS


def test_contract_registry_versions_match_their_family_names() -> None:
    for family, version in CONTRACT_SCHEMAS.items():
        assert version == f"{family}/v1"
