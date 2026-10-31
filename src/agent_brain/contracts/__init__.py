"""Stable, product-neutral data contracts shared across Agent Brain slices."""

from agent_brain.contracts.evidence import ClaimRef, EvidenceRef
from agent_brain.contracts.improvement import (
    ALLOWED_LIFECYCLE_TRANSITIONS,
    DedupeRelationKind,
    Improvement,
    ImprovementLifecycle,
    ImprovementMergeLineage,
    ImprovementObservation,
    ImprovementPriority,
    ImprovementRelation,
    ImprovementWorkRef,
    WorkRefKind,
    build_improvement_id,
    derive_recurrence,
    is_lifecycle_transition_allowed,
    normalize_root_cause_key,
    require_lifecycle_transition,
)
from agent_brain.contracts.index import GraphEdge, IndexRecord, graph_fingerprint
from agent_brain.contracts.provenance import Provenance, SourceSpan
from agent_brain.contracts.registry import CONTRACT_SCHEMAS
from agent_brain.contracts.repository import ArtifactRef, RepositoryProfile, RepositorySource
from agent_brain.contracts.resolution import ResolutionMeta, ResolutionState
from agent_brain.contracts.serialization import contract_payload, serialize_contract
from agent_brain.contracts.temporal import TemporalEnvelope
from agent_brain.contracts.versioning import ContractVersion, require_compatible_version

__all__ = [
    "ALLOWED_LIFECYCLE_TRANSITIONS",
    "CONTRACT_SCHEMAS",
    "ArtifactRef",
    "ClaimRef",
    "ContractVersion",
    "DedupeRelationKind",
    "EvidenceRef",
    "GraphEdge",
    "Improvement",
    "ImprovementLifecycle",
    "ImprovementMergeLineage",
    "ImprovementObservation",
    "ImprovementPriority",
    "ImprovementRelation",
    "ImprovementWorkRef",
    "IndexRecord",
    "Provenance",
    "RepositoryProfile",
    "RepositorySource",
    "ResolutionMeta",
    "ResolutionState",
    "SourceSpan",
    "TemporalEnvelope",
    "WorkRefKind",
    "build_improvement_id",
    "contract_payload",
    "derive_recurrence",
    "graph_fingerprint",
    "is_lifecycle_transition_allowed",
    "normalize_root_cause_key",
    "require_compatible_version",
    "require_lifecycle_transition",
    "serialize_contract",
]
