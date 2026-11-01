"""Host-neutral Agent Brain Capability Layer (#73 Goal 1).

Architecture::

    Agent Brain generic Core
            ↓
    agent_brain.protocol (#12)
            ↓
    agent_brain.capabilities   ← this package
            ↓
    cdb_context profile
            ↓
    host-neutral descriptors
            ↓
    future host adapters

CDB-specific policy lives under ``agent_brain.capabilities.cdb_context`` and must
not leak into generic core packages. Host adapters only package / transport.
"""

from __future__ import annotations

from agent_brain.capabilities.contract import (
    CAPABILITY_CONTRACT_MAJOR,
    CAPABILITY_CONTRACT_SCHEMA,
    SUPPORTED_CONTRACT_SCHEMAS,
    CapabilityContract,
    assert_compatible_contract_version,
    contract_metadata,
    current_capability_contract,
)
from agent_brain.capabilities.descriptors import (
    CAPABILITY_DESCRIPTOR_SCHEMA,
    capability_tool_descriptors,
)
from agent_brain.capabilities.freshness import (
    FRESHNESS_CURRENT,
    FRESHNESS_STALE,
    FRESHNESS_SUPERSEDED,
    FRESHNESS_UNKNOWN,
    LIMITATION_NO_EVIDENCE,
    LIMITATION_PARTIAL,
    LIMITATION_UNAVAILABLE,
    AuthoritativeSelection,
    prefer_live_over_persisted,
)
from agent_brain.capabilities.gateway import CapabilityGateway, invoke_capability
from agent_brain.capabilities.mapping import (
    CAPABILITY_MAPPINGS,
    BackendKind,
    CapabilityMapping,
    mapping_for,
)
from agent_brain.capabilities.names import (
    AGENT_BRAIN_HEALTH,
    CAPABILITY_NAME,
    CDB_CONTEXT_BRIEFING,
    CDB_CONTEXT_EVIDENCE,
    CDB_CONTEXT_REQUIRED_READS,
    CDB_CONTEXT_SEARCH,
    FORBIDDEN_ALTERNATE_PRODUCT_NAMES,
    OPTIONAL_CAPABILITY_NAMES,
    PRODUCT_NAME,
    REQUIRED_CAPABILITY_NAMES,
)

__all__ = [
    "AGENT_BRAIN_HEALTH",
    "CAPABILITY_CONTRACT_MAJOR",
    "CAPABILITY_CONTRACT_SCHEMA",
    "CAPABILITY_DESCRIPTOR_SCHEMA",
    "CAPABILITY_MAPPINGS",
    "CAPABILITY_NAME",
    "CDB_CONTEXT_BRIEFING",
    "CDB_CONTEXT_EVIDENCE",
    "CDB_CONTEXT_REQUIRED_READS",
    "CDB_CONTEXT_SEARCH",
    "FORBIDDEN_ALTERNATE_PRODUCT_NAMES",
    "FRESHNESS_CURRENT",
    "FRESHNESS_STALE",
    "FRESHNESS_SUPERSEDED",
    "FRESHNESS_UNKNOWN",
    "LIMITATION_NO_EVIDENCE",
    "LIMITATION_PARTIAL",
    "LIMITATION_UNAVAILABLE",
    "OPTIONAL_CAPABILITY_NAMES",
    "PRODUCT_NAME",
    "REQUIRED_CAPABILITY_NAMES",
    "SUPPORTED_CONTRACT_SCHEMAS",
    "AuthoritativeSelection",
    "BackendKind",
    "CapabilityContract",
    "CapabilityGateway",
    "CapabilityMapping",
    "assert_compatible_contract_version",
    "capability_tool_descriptors",
    "contract_metadata",
    "current_capability_contract",
    "invoke_capability",
    "mapping_for",
    "prefer_live_over_persisted",
]
