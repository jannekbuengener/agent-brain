"""Memory Read / Recall / Rediscovery surface (#11 / Slice 10).

Consumes #39 MemoryStore/MemoryScope and #37 temporal/provenance/supersession
contracts. Does not introduce productive write APIs or a second store/scope.
"""

from __future__ import annotations

from agent_brain.memory.read.catalog import MemoryEntryCatalog, entry_from_parts
from agent_brain.memory.read.freshness import (
    FreshnessDerivation,
    derive_memory_resolution_state,
)
from agent_brain.memory.read.knowledge_boundary import (
    assert_not_mixed,
    classify_knowledge_result,
    classify_memory_read_result,
)
from agent_brain.memory.read.live_state import (
    DEFAULT_LIVE_SOURCE_PRIORITY,
    LiveStateChecker,
    LiveStateObservation,
    StaticLiveStateChecker,
    revalidate_against_live_state,
)
from agent_brain.memory.read.models import (
    ARTIFACT_KIND_MEMORY,
    LIVE_CLAIM_SCHEMA,
    LIVE_REVALIDATION_SCHEMA,
    MEMORY_ENTRY_SCHEMA,
    MEMORY_READ_ITEM_SCHEMA,
    MEMORY_READ_RESULT_SCHEMA,
    ArtifactKind,
    LiveRevalidationResult,
    LiveRevalidationStatus,
    LiveStateClaim,
    MemoryEntry,
    MemoryReadItem,
    MemoryReadResult,
)
from agent_brain.memory.read.provenance_gate import (
    ProvenanceGateResult,
    evaluate_provenance_gate,
)
from agent_brain.memory.read.rediscovery import (
    REDISCOVERY_PROOF_SCHEMA,
    RediscoveryProof,
    prove_cross_session_rediscovery,
)
from agent_brain.memory.read.service import MemoryReadService, assert_scopes_isolated

__all__ = [
    "ARTIFACT_KIND_MEMORY",
    "DEFAULT_LIVE_SOURCE_PRIORITY",
    "LIVE_CLAIM_SCHEMA",
    "LIVE_REVALIDATION_SCHEMA",
    "MEMORY_ENTRY_SCHEMA",
    "MEMORY_READ_ITEM_SCHEMA",
    "MEMORY_READ_RESULT_SCHEMA",
    "REDISCOVERY_PROOF_SCHEMA",
    "ArtifactKind",
    "FreshnessDerivation",
    "LiveRevalidationResult",
    "LiveRevalidationStatus",
    "LiveStateChecker",
    "LiveStateClaim",
    "LiveStateObservation",
    "MemoryEntry",
    "MemoryEntryCatalog",
    "MemoryReadItem",
    "MemoryReadResult",
    "MemoryReadService",
    "ProvenanceGateResult",
    "RediscoveryProof",
    "StaticLiveStateChecker",
    "assert_not_mixed",
    "assert_scopes_isolated",
    "classify_knowledge_result",
    "classify_memory_read_result",
    "derive_memory_resolution_state",
    "entry_from_parts",
    "evaluate_provenance_gate",
    "prove_cross_session_rediscovery",
    "revalidate_against_live_state",
]
