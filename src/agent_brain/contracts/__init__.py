"""Stable, product-neutral data contracts shared across Agent Brain slices."""

from agent_brain.contracts.serialization import contract_payload, serialize_contract
from agent_brain.contracts.versioning import ContractVersion, require_compatible_version

__all__ = [
    "ContractVersion",
    "contract_payload",
    "require_compatible_version",
    "serialize_contract",
]
