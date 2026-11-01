"""Shared MCP transport for host adapters (#73 Goals 2–3).

Forwards only the bounded ``cdb_context`` capability surface through
``CapabilityGateway``. No MCP SDK dependency. No Claire runtime. No private
operator ChatGPT MCP. Host adapters package/register this entrypoint; they must
not reimplement capability semantics.

Transports:
- stdio: ``agent-brain-mcp`` / ``python -m agent_brain.mcp``
- Streamable HTTP: ``agent-brain-mcp-http`` / ``python -m agent_brain.mcp.http``
"""

from __future__ import annotations

from agent_brain.mcp.server import MCP_SERVER_NAME, MCP_SERVER_SCHEMA, serve_stdio
from agent_brain.mcp.transport import (
    CapabilityMcpTransport,
    mcp_tool_annotations,
    mcp_tool_definitions,
)

# Avoid eager-importing ``agent_brain.mcp.http`` here so ``python -m agent_brain.mcp.http``
# is not shadowed by package ``__init__`` side effects (runpy warning / hung entry).

__all__ = [
    "MCP_HTTP_SCHEMA",
    "MCP_SERVER_NAME",
    "MCP_SERVER_SCHEMA",
    "CapabilityMcpTransport",
    "create_http_server",
    "mcp_tool_annotations",
    "mcp_tool_definitions",
    "serve_http",
    "serve_stdio",
]


def __getattr__(name: str):
    if name in {"MCP_HTTP_SCHEMA", "create_http_server", "serve_http"}:
        from agent_brain.mcp import http as _http

        mapping = {
            "MCP_HTTP_SCHEMA": _http.MCP_HTTP_SCHEMA,
            "create_http_server": _http.create_http_server,
            "serve_http": _http.serve_http,
        }
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
