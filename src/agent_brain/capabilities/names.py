"""Host-facing capability names for the Agent Brain plugin surface (#73).

Internal #12 protocol operation names stay unchanged. These names are the
stable, host-neutral Capability Contract identities that adapters must expose.
"""

from __future__ import annotations

PRODUCT_NAME = "Agent Brain"
CAPABILITY_NAME = "cdb_context"

AGENT_BRAIN_HEALTH = "agent_brain.health"
CDB_CONTEXT_BRIEFING = "cdb_context.briefing"
CDB_CONTEXT_SEARCH = "cdb_context.search"
CDB_CONTEXT_REQUIRED_READS = "cdb_context.required_reads"
CDB_CONTEXT_EVIDENCE = "cdb_context.evidence"

REQUIRED_CAPABILITY_NAMES = frozenset(
    {
        AGENT_BRAIN_HEALTH,
        CDB_CONTEXT_BRIEFING,
        CDB_CONTEXT_SEARCH,
        CDB_CONTEXT_REQUIRED_READS,
        CDB_CONTEXT_EVIDENCE,
    }
)

# Optional host-facing names — only exposed when core already supports them.
OPTIONAL_CAPABILITY_NAMES = frozenset(
    {
        "cdb_context.decision_history",
        "cdb_context.impact",
    }
)

FORBIDDEN_ALTERNATE_PRODUCT_NAMES = frozenset(
    {
        "CDB Context Plugin",
        "cdb context plugin",
        "CDB Context",
    }
)

__all__ = [
    "AGENT_BRAIN_HEALTH",
    "CAPABILITY_NAME",
    "CDB_CONTEXT_BRIEFING",
    "CDB_CONTEXT_EVIDENCE",
    "CDB_CONTEXT_REQUIRED_READS",
    "CDB_CONTEXT_SEARCH",
    "FORBIDDEN_ALTERNATE_PRODUCT_NAMES",
    "OPTIONAL_CAPABILITY_NAMES",
    "PRODUCT_NAME",
    "REQUIRED_CAPABILITY_NAMES",
]
