"""CDB-specific ``cdb_context`` profile and thin capability composers (#73)."""

from __future__ import annotations

from agent_brain.capabilities.cdb_context.profile import (
    CDB_GITHUB_TREE_BASE,
    CDB_GUARDRAILS,
    CDB_REPOSITORY_IDENTITY,
    CDB_REPOSITORY_NAME,
    CDB_REPOSITORY_OWNER,
    CDB_SOURCE_PRIORITY,
    CdbContextProfile,
    build_cdb_required_reads_profile,
    default_cdb_context_profile,
)
from agent_brain.capabilities.cdb_context.surface import (
    invoke_briefing,
    invoke_evidence,
    invoke_required_reads,
    invoke_search,
)

__all__ = [
    "CDB_GITHUB_TREE_BASE",
    "CDB_GUARDRAILS",
    "CDB_REPOSITORY_IDENTITY",
    "CDB_REPOSITORY_NAME",
    "CDB_REPOSITORY_OWNER",
    "CDB_SOURCE_PRIORITY",
    "CdbContextProfile",
    "build_cdb_required_reads_profile",
    "default_cdb_context_profile",
    "invoke_briefing",
    "invoke_evidence",
    "invoke_required_reads",
    "invoke_search",
]
