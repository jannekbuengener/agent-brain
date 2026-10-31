"""Memory / store boundary (#39) and Memory Read surface (#11).

Backend-neutral read-only ports for KnowledgeStore and MemoryStore, plus a
typed fail-closed MemoryScope. Slice #11 adds recall evaluation, freshness,
live-state revalidation, and cross-session rediscovery on top of those ports.
No productive write surface lives here.
"""

from __future__ import annotations

from agent_brain.memory.errors import (
    InvalidMemoryScope,
    MemoryBoundaryError,
    StoreUnavailableError,
)
from agent_brain.memory.in_memory import InMemoryKnowledgeStore, InMemoryMemoryStore
from agent_brain.memory.ports import (
    FORBIDDEN_WRITE_METHODS,
    KnowledgeStore,
    MemoryStore,
    assert_read_only_store,
)
from agent_brain.memory.read import (
    ARTIFACT_KIND_MEMORY,
    MEMORY_ENTRY_SCHEMA,
    MEMORY_READ_ITEM_SCHEMA,
    MEMORY_READ_RESULT_SCHEMA,
    REDISCOVERY_PROOF_SCHEMA,
    ArtifactKind,
    MemoryEntry,
    MemoryEntryCatalog,
    MemoryReadItem,
    MemoryReadResult,
    MemoryReadService,
    RediscoveryProof,
    StaticLiveStateChecker,
    derive_memory_resolution_state,
    entry_from_parts,
    prove_cross_session_rediscovery,
)
from agent_brain.memory.scope import MEMORY_SCOPE_SCHEMA, MemoryScope, MemoryScopeKind
from agent_brain.memory.types import (
    KNOWLEDGE_QUERY_SCHEMA,
    KNOWLEDGE_RESULT_SCHEMA,
    KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
    MEMORY_RECALL_QUERY_SCHEMA,
    MEMORY_RECALL_RESULT_SCHEMA,
    MEMORY_RECORD_SCHEMA,
    STORE_HEALTH_SCHEMA,
    KnowledgeHit,
    KnowledgeQuery,
    KnowledgeResult,
    KnowledgeSnapshotLookup,
    LookupStatus,
    MemoryRecallQuery,
    MemoryRecallResult,
    MemoryRecord,
    ResultCardinality,
    StoreAvailability,
    StoreHealth,
    default_store_health,
    require_memory_scope,
)
from agent_brain.memory.unavailable import (
    UnavailableKnowledgeStore,
    UnavailableMemoryStore,
)

__all__ = [
    "ARTIFACT_KIND_MEMORY",
    "FORBIDDEN_WRITE_METHODS",
    "KNOWLEDGE_QUERY_SCHEMA",
    "KNOWLEDGE_RESULT_SCHEMA",
    "KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA",
    "MEMORY_ENTRY_SCHEMA",
    "MEMORY_READ_ITEM_SCHEMA",
    "MEMORY_READ_RESULT_SCHEMA",
    "MEMORY_RECALL_QUERY_SCHEMA",
    "MEMORY_RECALL_RESULT_SCHEMA",
    "MEMORY_RECORD_SCHEMA",
    "MEMORY_SCOPE_SCHEMA",
    "REDISCOVERY_PROOF_SCHEMA",
    "STORE_HEALTH_SCHEMA",
    "ArtifactKind",
    "InMemoryKnowledgeStore",
    "InMemoryMemoryStore",
    "InvalidMemoryScope",
    "KnowledgeHit",
    "KnowledgeQuery",
    "KnowledgeResult",
    "KnowledgeSnapshotLookup",
    "KnowledgeStore",
    "LookupStatus",
    "MemoryBoundaryError",
    "MemoryEntry",
    "MemoryEntryCatalog",
    "MemoryReadItem",
    "MemoryReadResult",
    "MemoryReadService",
    "MemoryRecallQuery",
    "MemoryRecallResult",
    "MemoryRecord",
    "MemoryScope",
    "MemoryScopeKind",
    "MemoryStore",
    "RediscoveryProof",
    "ResultCardinality",
    "StaticLiveStateChecker",
    "StoreAvailability",
    "StoreHealth",
    "StoreUnavailableError",
    "UnavailableKnowledgeStore",
    "UnavailableMemoryStore",
    "assert_read_only_store",
    "default_store_health",
    "derive_memory_resolution_state",
    "entry_from_parts",
    "prove_cross_session_rediscovery",
    "require_memory_scope",
]
