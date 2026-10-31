"""Public Application / Protocol Surface (#12).

Shared read-only contract between Agent Brain core and transports (CLI,
optional MCP, future consumers). Domain logic remains in existing packages;
this module only exposes stable request/response, health, capability, and
error envelopes bound to the #17 package version.
"""

from __future__ import annotations

from agent_brain.protocol.errors import (
    EXIT_INTERNAL,
    EXIT_INVALID,
    EXIT_SUCCESS,
    EXIT_UNAVAILABLE,
    EXIT_UNSUPPORTED,
    ProtocolError,
    ProtocolErrorCode,
    exit_code_for,
)
from agent_brain.protocol.gateway import ProtocolGateway, invoke
from agent_brain.protocol.mcp_adapter import MCP_ADAPTER_SCHEMA, BrainMcpAdapter, tool_schemas
from agent_brain.protocol.models import (
    DOMAIN_OPERATIONS,
    FORBIDDEN_WRITE_OPERATIONS,
    META_OPERATIONS,
    PROTOCOL_SCHEMA,
    PUBLIC_OPERATIONS,
    CapabilityId,
    CapabilityReport,
    CapabilityState,
    CapabilityStatus,
    ComponentHealth,
    HealthReport,
    HealthState,
    ProtocolRequest,
    ProtocolResponse,
    agent_brain_version_metadata,
    failure_response,
    success_response,
)
from agent_brain.protocol.runtime import ProtocolRuntime, default_runtime

__all__ = [
    "DOMAIN_OPERATIONS",
    "EXIT_INTERNAL",
    "EXIT_INVALID",
    "EXIT_SUCCESS",
    "EXIT_UNAVAILABLE",
    "EXIT_UNSUPPORTED",
    "FORBIDDEN_WRITE_OPERATIONS",
    "MCP_ADAPTER_SCHEMA",
    "META_OPERATIONS",
    "PROTOCOL_SCHEMA",
    "PUBLIC_OPERATIONS",
    "BrainMcpAdapter",
    "CapabilityId",
    "CapabilityReport",
    "CapabilityState",
    "CapabilityStatus",
    "ComponentHealth",
    "HealthReport",
    "HealthState",
    "ProtocolError",
    "ProtocolErrorCode",
    "ProtocolGateway",
    "ProtocolRequest",
    "ProtocolResponse",
    "ProtocolRuntime",
    "agent_brain_version_metadata",
    "default_runtime",
    "exit_code_for",
    "failure_response",
    "invoke",
    "success_response",
    "tool_schemas",
]
