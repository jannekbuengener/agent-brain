"""Portable host MCP registration snippets (no absolute user paths)."""

from __future__ import annotations

from agent_brain import __version__
from agent_brain.capabilities import CAPABILITY_CONTRACT_SCHEMA
from agent_brain.mcp.server import MCP_SERVER_NAME, MCP_SERVER_SCHEMA

# Portable stdio launch: console script from ``pip install agent-brain==X.Y.Z``.
# Prefer the entrypoint over bare ``python -m ...`` so multi-Python PATH setups
# (Windows) do not pick an interpreter without agent-brain installed.
STDIO_COMMAND = "agent-brain-mcp"
STDIO_ARGS: tuple[str, ...] = ()
# Documented fallback when the console script is unavailable:
MODULE_FALLBACK_COMMAND = "python"
MODULE_FALLBACK_ARGS: tuple[str, ...] = ("-m", "agent_brain.mcp")


def shared_stdio_launch() -> dict[str, object]:
    return {
        "command": STDIO_COMMAND,
        "args": list(STDIO_ARGS),
    }


def claude_code_mcp_json() -> dict[str, object]:
    """Claude Code plugin ``.mcp.json`` shape (stdio via console script)."""
    launch = shared_stdio_launch()
    return {
        "mcpServers": {
            MCP_SERVER_NAME: {
                "command": launch["command"],
                "args": launch["args"],
            }
        }
    }


def cursor_agent_plugin_mcp_json() -> dict[str, object]:
    """Cursor / Agent Plugins ``mcp.json`` shape."""
    launch = shared_stdio_launch()
    return {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        "mcpServers": {
            MCP_SERVER_NAME: {
                "type": "stdio",
                "command": launch["command"],
                "args": launch["args"],
            }
        },
    }


def opencode_mcp_config() -> dict[str, object]:
    """OpenCode ``opencode.json`` ``mcp`` fragment."""
    return {
        "mcp": {
            MCP_SERVER_NAME: {
                "type": "local",
                "command": [STDIO_COMMAND, *STDIO_ARGS],
                "enabled": True,
            }
        }
    }


def foundation_metadata() -> dict[str, object]:
    return {
        "product_name": "Agent Brain",
        "mcp_server_name": MCP_SERVER_NAME,
        "mcp_server_schema": MCP_SERVER_SCHEMA,
        "capability_contract_schema": CAPABILITY_CONTRACT_SCHEMA,
        "agent_brain_version": __version__,
        "pin": f"agent-brain=={__version__}",
        "git_tag": f"v{__version__}",
        "read_only": True,
    }


__all__ = [
    "MODULE_FALLBACK_ARGS",
    "MODULE_FALLBACK_COMMAND",
    "STDIO_ARGS",
    "STDIO_COMMAND",
    "claude_code_mcp_json",
    "cursor_agent_plugin_mcp_json",
    "foundation_metadata",
    "opencode_mcp_config",
    "shared_stdio_launch",
]
