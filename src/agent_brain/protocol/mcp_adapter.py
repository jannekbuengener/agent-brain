"""Optional host-neutral MCP adapter descriptors (#12).

This module does **not** depend on any MCP SDK or the private ChatGPT MCP.
Adapters may bind these schemas to a concrete transport. The Agent Brain core
remains fully usable without importing this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_brain.protocol.errors import ProtocolError
from agent_brain.protocol.gateway import ProtocolGateway
from agent_brain.protocol.models import PROTOCOL_SCHEMA, PUBLIC_OPERATIONS, ProtocolRequest
from agent_brain.protocol.runtime import ProtocolRuntime, default_runtime

MCP_ADAPTER_SCHEMA = "agent-brain-mcp-adapter/v1"


def tool_schemas() -> dict[str, object]:
    """Host-neutral tool descriptors for an optional brain-mcp adapter."""
    tools: dict[str, object] = {}
    for operation in sorted(PUBLIC_OPERATIONS):
        tools[operation] = {
            "name": operation,
            "description": f"Agent Brain read-only protocol operation '{operation}'",
            "input": {"payload": "object"},
            "output": "ProtocolResponse",
            "read_only": True,
        }
    return {
        "schema_version": MCP_ADAPTER_SCHEMA,
        "protocol_schema": PROTOCOL_SCHEMA,
        "transport": "host-neutral",
        "requires_mcp_sdk": False,
        "requires_private_operator_mcp": False,
        "tools": tools,
    }


class BrainMcpAdapter:
    """Thin MCP-shaped facade that only forwards to ProtocolGateway."""

    def __init__(self, runtime: ProtocolRuntime | None = None) -> None:
        self._gateway = ProtocolGateway(runtime=runtime if runtime is not None else default_runtime())

    @property
    def gateway(self) -> ProtocolGateway:
        return self._gateway

    def list_tools(self) -> dict[str, object]:
        return tool_schemas()

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> dict[str, object]:
        payload = dict(arguments or {})
        # Allow either bare payload or {payload: {...}} wrappers from hosts.
        if "payload" in payload and isinstance(payload["payload"], Mapping):
            inner = dict(payload["payload"])
        else:
            inner = payload
        try:
            request = ProtocolRequest(operation=name, payload=inner, request_id=request_id)
        except ProtocolError as exc:
            from agent_brain.protocol.models import failure_response

            return failure_response(name or "invalid", exc).to_dict()
        return self._gateway.invoke_sync(request).to_dict()


__all__ = [
    "MCP_ADAPTER_SCHEMA",
    "BrainMcpAdapter",
    "tool_schemas",
]
