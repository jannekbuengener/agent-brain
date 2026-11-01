"""Host-neutral capability / tool descriptors for future adapters (#73).

Composes the existing #12 ``tool_schemas`` / ``BrainMcpAdapter`` surface.
No MCP SDK dependency. No host names in capability definitions.
"""

from __future__ import annotations

from agent_brain.capabilities.contract import (
    CAPABILITY_CONTRACT_SCHEMA,
    current_capability_contract,
)
from agent_brain.capabilities.mapping import CAPABILITY_MAPPINGS
from agent_brain.capabilities.names import PRODUCT_NAME, REQUIRED_CAPABILITY_NAMES
from agent_brain.protocol.mcp_adapter import MCP_ADAPTER_SCHEMA, tool_schemas

CAPABILITY_DESCRIPTOR_SCHEMA = "agent-brain-capability-descriptors/v1"

_CAPABILITY_INPUTS: dict[str, dict[str, object]] = {
    "agent_brain.health": {
        "type": "object",
        "properties": {
            "contract_version": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "cdb_context.briefing": {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "topic": {"type": "string"},
            "task_id": {"type": "string"},
            "contract_version": {"type": "string"},
            "evidence_refs": {"type": "array"},
        },
        "additionalProperties": True,
    },
    "cdb_context.search": {
        "type": "object",
        "properties": {
            "query": {"oneOf": [{"type": "string"}, {"type": "object"}]},
            "scope": {"type": "string"},
            "records": {"type": "array"},
            "contract_version": {"type": "string"},
        },
        "required": ["query"],
        "additionalProperties": True,
    },
    "cdb_context.required_reads": {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "topic": {"type": "string"},
            "available_paths": {"type": "array", "items": {"type": "string"}},
            "contract_version": {"type": "string"},
        },
        "additionalProperties": True,
    },
    "cdb_context.evidence": {
        "type": "object",
        "properties": {
            "ref": {"type": "string"},
            "claim": {"type": "string"},
            "query": {"type": "string"},
            "scope": {"type": "string"},
            "topic": {"type": "string"},
            "contract_version": {"type": "string"},
        },
        "additionalProperties": True,
    },
}


def capability_tool_descriptors() -> dict[str, object]:
    """Machine-readable host-neutral capability descriptors."""
    contract = current_capability_contract()
    tools: dict[str, object] = {}
    for name in sorted(REQUIRED_CAPABILITY_NAMES):
        mapping = CAPABILITY_MAPPINGS[name]
        tools[name] = {
            "name": name,
            "description": mapping.description,
            "input_schema": _CAPABILITY_INPUTS[name],
            "output_contract": "ProtocolResponse-compatible capability envelope",
            "read_only": True,
            "protocol_operation": mapping.protocol_operation,
            "domain_symbol": mapping.domain_symbol,
            "backend_kind": mapping.backend_kind.value,
            "limitations": [
                "read_only",
                "no_host_specific_semantics",
                "no_silent_contract_downgrade",
            ],
            "failure_semantics": [
                "invalid_input",
                "invalid_scope",
                "capability_unavailable",
                "backend_unavailable",
                "contract_version_mismatch",
                "internal_failure",
                "stale_or_partial_via_limitations_and_resolution_state",
                "no_evidence_explicit",
            ],
            "capability_contract_schema": CAPABILITY_CONTRACT_SCHEMA,
            "agent_brain_version": contract.agent_brain_version,
        }

    protocol = tool_schemas()
    return {
        "schema_version": CAPABILITY_DESCRIPTOR_SCHEMA,
        "product_name": PRODUCT_NAME,
        "capability_contract_schema": CAPABILITY_CONTRACT_SCHEMA,
        "agent_brain_version": contract.agent_brain_version,
        "protocol_schema": contract.protocol_schema,
        "mcp_adapter_schema": MCP_ADAPTER_SCHEMA,
        "transport": "host-neutral",
        "requires_mcp_sdk": False,
        "requires_private_operator_mcp": False,
        "read_only": True,
        "tools": tools,
        "protocol_tools": protocol.get("tools"),
        "adapter_responsibilities": [
            "packaging",
            "registration",
            "transport",
            "host_ux",
        ],
        "adapter_must_not": [
            "invent_context_semantics",
            "fork_capability_definitions_per_host",
            "silently_downgrade_contract_version",
        ],
    }


__all__ = [
    "CAPABILITY_DESCRIPTOR_SCHEMA",
    "capability_tool_descriptors",
]
