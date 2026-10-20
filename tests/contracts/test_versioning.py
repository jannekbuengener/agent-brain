from __future__ import annotations

import pytest

from agent_brain.contracts.serialization import contract_payload, serialize_contract
from agent_brain.contracts.versioning import ContractVersion, require_compatible_version


def test_contract_version_parses_family_and_major() -> None:
    version = ContractVersion.parse("repository-source/v1")

    assert version.family == "repository-source"
    assert version.major == 1
    assert str(version) == "repository-source/v1"


@pytest.mark.parametrize(
    "value",
    ["", "repository-source", "repository-source/v", "repository source/v1", "repository-source/v0"],
)
def test_contract_version_rejects_malformed_values(value: str) -> None:
    with pytest.raises(ValueError):
        ContractVersion.parse(value)


def test_require_compatible_version_accepts_same_family_and_major() -> None:
    version = require_compatible_version(
        "repository-source/v1",
        expected_family="repository-source",
        supported_major=1,
    )

    assert version == ContractVersion(family="repository-source", major=1)


def test_require_compatible_version_rejects_other_family() -> None:
    with pytest.raises(ValueError, match="family"):
        require_compatible_version(
            "claim-ref/v1",
            expected_family="repository-source",
            supported_major=1,
        )


def test_require_compatible_version_rejects_other_major() -> None:
    with pytest.raises(ValueError, match="major"):
        require_compatible_version(
            "repository-source/v2",
            expected_family="repository-source",
            supported_major=1,
        )


def test_contract_payload_and_serializer_are_deterministic() -> None:
    payload = contract_payload(schema_version="repository-source/v1", repository="example/widgets")

    assert payload == {
        "schema_version": "repository-source/v1",
        "repository": "example/widgets",
    }
    assert serialize_contract(payload) == (
        '{"repository":"example/widgets","schema_version":"repository-source/v1"}'
    )
