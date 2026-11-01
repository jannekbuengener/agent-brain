"""Capability → MCP tool binding (host-neutral, SDK-free)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from agent_brain.capabilities import (
    AGENT_BRAIN_HEALTH,
    REQUIRED_CAPABILITY_NAMES,
    CapabilityGateway,
    capability_tool_descriptors,
    invoke_capability,
)
from agent_brain.protocol.models import ProtocolResponse
from agent_brain.protocol.runtime import ProtocolRuntime

# Host metadata only. Server safety does not depend on these hints.
# openWorldHint: health is bounded local; cdb_context tools may consult
# GitHub Live / public repo sources (prefer_live_over_persisted).
_TOOL_ANNOTATIONS: dict[str, dict[str, bool]] = {
    AGENT_BRAIN_HEALTH: {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "cdb_context.briefing": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
    "cdb_context.search": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
    "cdb_context.required_reads": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
    "cdb_context.evidence": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
}


def mcp_tool_annotations(name: str) -> dict[str, bool]:
    """Return MCP tool annotations for a bounded capability name."""
    try:
        return dict(_TOOL_ANNOTATIONS[name])
    except KeyError as exc:
        raise KeyError(f"no annotations for unexpected tool: {name}") from exc


def mcp_tool_definitions() -> list[dict[str, object]]:
    """MCP ``tools/list`` payload derived from host-neutral descriptors."""
    descriptors = capability_tool_descriptors()
    tools_meta = descriptors["tools"]
    assert isinstance(tools_meta, Mapping)
    tools: list[dict[str, object]] = []
    for name in sorted(REQUIRED_CAPABILITY_NAMES):
        meta = tools_meta[name]
        assert isinstance(meta, Mapping)
        tools.append(
            {
                "name": name,
                "title": name,
                "description": meta["description"],
                "inputSchema": meta["input_schema"],
                "annotations": mcp_tool_annotations(name),
            }
        )
    return tools


class CapabilityMcpTransport:
    """Thin MCP-shaped facade that only forwards to ``CapabilityGateway``."""

    def __init__(
        self,
        runtime: ProtocolRuntime | None = None,
        *,
        gateway: CapabilityGateway | None = None,
    ) -> None:
        self._gateway = gateway if gateway is not None else CapabilityGateway(runtime=runtime)

    @property
    def gateway(self) -> CapabilityGateway:
        return self._gateway

    def list_tools(self) -> list[dict[str, object]]:
        return mcp_tool_definitions()

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> ProtocolResponse:
        payload = dict(arguments or {})
        if "payload" in payload and isinstance(payload["payload"], Mapping):
            inner = dict(payload["payload"])
        else:
            inner = payload
        return self._gateway.invoke(name, inner, request_id=request_id)

    def call_tool_mcp_result(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> dict[str, object]:
        """Return an MCP ``tools/call`` result object (no semantic remapping)."""
        response = self.call_tool(name, arguments, request_id=request_id)
        body = response.to_dict()
        text = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return {
            "content": [{"type": "text", "text": text}],
            "structuredContent": body,
            "isError": not response.ok,
        }


def invoke_via_transport(
    capability: str,
    payload: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ProtocolResponse:
    """Suite-compatible invoke that uses the shared MCP transport facade."""
    return invoke_capability(capability, payload, **kwargs)


__all__ = [
    "CapabilityMcpTransport",
    "invoke_via_transport",
    "mcp_tool_annotations",
    "mcp_tool_definitions",
]
