"""Memory / store boundary (#39).

Backend-neutral read-only ports for KnowledgeStore and MemoryStore, plus a
typed fail-closed MemoryScope. No productive write surface lives here.
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
    "FORBIDDEN_WRITE_METHODS",
    "KNOWLEDGE_QUERY_SCHEMA",
    "KNOWLEDGE_RESULT_SCHEMA",
    "KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA",
    "MEMORY_RECALL_QUERY_SCHEMA",
    "MEMORY_RECALL_RESULT_SCHEMA",
    "MEMORY_RECORD_SCHEMA",
    "MEMORY_SCOPE_SCHEMA",
    "STORE_HEALTH_SCHEMA",
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
    "MemoryRecallQuery",
    "MemoryRecallResult",
    "MemoryRecord",
    "MemoryScope",
    "MemoryScopeKind",
    "MemoryStore",
    "ResultCardinality",
    "StoreAvailability",
    "StoreHealth",
    "StoreUnavailableError",
    "UnavailableKnowledgeStore",
    "UnavailableMemoryStore",
    "assert_read_only_store",
    "default_store_health",
    "require_memory_scope",
]
