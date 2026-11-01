"""Shared stdio MCP transport for host adapters (#73 Goal 2).

Forwards only the bounded ``cdb_context`` capability surface through
``CapabilityGateway``. No MCP SDK dependency. No Claire runtime. No private
ChatGPT MCP. Host adapters package/register this entrypoint; they must not
reimplement capability semantics.
"""

from __future__ import annotations

from agent_brain.mcp.server import MCP_SERVER_NAME, MCP_SERVER_SCHEMA, serve_stdio
from agent_brain.mcp.transport import CapabilityMcpTransport, mcp_tool_definitions

__all__ = [
    "MCP_SERVER_NAME",
    "MCP_SERVER_SCHEMA",
    "CapabilityMcpTransport",
    "mcp_tool_definitions",
    "serve_stdio",
]
