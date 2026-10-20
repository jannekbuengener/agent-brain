"""Stable, product-neutral data contracts shared across Agent Brain slices."""

from agent_brain.contracts.evidence import ClaimRef, EvidenceRef
from agent_brain.contracts.index import GraphEdge, IndexRecord, graph_fingerprint
from agent_brain.contracts.registry import CONTRACT_SCHEMAS
from agent_brain.contracts.repository import ArtifactRef, RepositoryProfile, RepositorySource
from agent_brain.contracts.serialization import contract_payload, serialize_contract
from agent_brain.contracts.versioning import ContractVersion, require_compatible_version

__all__ = [
    "ArtifactRef",
    "CONTRACT_SCHEMAS",
    "ClaimRef",
    "ContractVersion",
    "EvidenceRef",
    "GraphEdge",
    "IndexRecord",
    "RepositoryProfile",
    "RepositorySource",
    "contract_payload",
    "graph_fingerprint",
    "require_compatible_version",
    "serialize_contract",
]
