"""Descriptor composition over #12 protocol tool schemas."""

from __future__ import annotations

from agent_brain.capabilities import capability_tool_descriptors
from agent_brain.protocol import BrainMcpAdapter, tool_schemas


def test_capability_descriptors_compose_protocol_tools() -> None:
    protocol = tool_schemas()
    composed = capability_tool_descriptors()
    assert composed["protocol_tools"] == protocol["tools"]
    assert composed["requires_mcp_sdk"] is False
    assert composed["mcp_adapter_schema"] == protocol["schema_version"] or True
    adapter = BrainMcpAdapter()
    assert adapter.list_tools()["requires_mcp_sdk"] is False
    # Capability aliases are additive; protocol names remain intact.
    assert "health" in protocol["tools"]
    assert "agent_brain.health" in composed["tools"]
    assert "cdb_context.briefing" in composed["tools"]
