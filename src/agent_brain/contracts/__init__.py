"""Stable, product-neutral data contracts shared across Agent Brain slices."""

from agent_brain.contracts.evidence import ClaimRef, EvidenceRef
from agent_brain.contracts.index import GraphEdge, IndexRecord, graph_fingerprint
from agent_brain.contracts.provenance import Provenance, SourceSpan
from agent_brain.contracts.registry import CONTRACT_SCHEMAS
from agent_brain.contracts.repository import ArtifactRef, RepositoryProfile, RepositorySource
from agent_brain.contracts.resolution import ResolutionMeta, ResolutionState
from agent_brain.contracts.serialization import contract_payload, serialize_contract
from agent_brain.contracts.temporal import TemporalEnvelope
from agent_brain.contracts.versioning import ContractVersion, require_compatible_version

__all__ = [
    "CONTRACT_SCHEMAS",
    "ArtifactRef",
    "ClaimRef",
    "ContractVersion",
    "EvidenceRef",
    "GraphEdge",
    "IndexRecord",
    "Provenance",
    "RepositoryProfile",
    "RepositorySource",
    "ResolutionMeta",
    "ResolutionState",
    "SourceSpan",
    "TemporalEnvelope",
    "contract_payload",
    "graph_fingerprint",
    "require_compatible_version",
    "serialize_contract",
]
