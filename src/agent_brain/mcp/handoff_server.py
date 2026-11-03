"""Stdio MCP entry for shared-memory handoff (reuses McpStdioServer runtime)."""

from __future__ import annotations

from agent_brain.mcp.handoff_transport import (
    HANDOFF_MCP_INSTRUCTIONS,
    HANDOFF_MCP_SCHEMA,
    HANDOFF_MCP_SERVER_NAME,
    HandoffMcpTransport,
    build_default_handoff_gateway,
)
from agent_brain.mcp.server import McpStdioServer, serve_stdio


def build_handoff_stdio_server(
    transport: HandoffMcpTransport | None = None,
) -> McpStdioServer:
    facade = transport if transport is not None else HandoffMcpTransport(build_default_handoff_gateway())
    return McpStdioServer(
        transport=facade,
        server_name=HANDOFF_MCP_SERVER_NAME,
        server_schema=HANDOFF_MCP_SCHEMA,
        instructions=HANDOFF_MCP_INSTRUCTIONS,
        read_only=False,
        capability_contract_schema=None,
        reject_as_read_only_surface=False,
    )


def main(argv: list[str] | None = None) -> int:
    del argv
    return serve_stdio(server=build_handoff_stdio_server())


if __name__ == "__main__":
    raise SystemExit(main())
