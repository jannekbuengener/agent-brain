"""Portable host MCP registration snippets (no absolute user paths)."""

from __future__ import annotations

from agent_brain import __version__
from agent_brain.capabilities import CAPABILITY_CONTRACT_SCHEMA
from agent_brain.mcp.http import DEFAULT_PATH, DEFAULT_PORT, MCP_HTTP_SCHEMA
from agent_brain.mcp.server import MCP_SERVER_NAME, MCP_SERVER_SCHEMA

# Portable stdio launch: console script from ``pip install agent-brain==X.Y.Z``.
# Prefer the entrypoint over bare ``python -m ...`` so multi-Python PATH setups
# (Windows) do not pick an interpreter without agent-brain installed.
STDIO_COMMAND = "agent-brain-mcp"
STDIO_ARGS: tuple[str, ...] = ()
HTTP_COMMAND = "agent-brain-mcp-http"
HTTP_ARGS: tuple[str, ...] = ()
# Documented fallback when the console script is unavailable:
MODULE_FALLBACK_COMMAND = "python"
MODULE_FALLBACK_ARGS: tuple[str, ...] = ("-m", "agent_brain.mcp")
HTTP_MODULE_FALLBACK_ARGS: tuple[str, ...] = ("-m", "agent_brain.mcp.http")

# Auth classification for ChatGPT remote packaging (no secrets; no OAuth invented).
# Sources used by the bounded cdb_context surface are public/read-only or
# operator-local fixtures — not user-scoped private account data.
CHATGPT_AUTH_MODEL = "PUBLIC_READ_ONLY"
CHATGPT_AUTH_TYPE = "none"


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


def chatgpt_remote_mcp_json(
    *,
    server_url: str | None = None,
    use_secure_mcp_tunnel: bool = True,
) -> dict[str, object]:
    """ChatGPT / Agent Plugins MCP declaration for remote or tunnel connection.

    Preferred Goal-3 development path is Secure MCP Tunnel to local
    ``agent-brain-mcp`` (stdio) or ``agent-brain-mcp-http`` (``/mcp``).
    ``server_url`` is a placeholder HTTPS ``/mcp`` endpoint for stable remote
    installs — never commit secrets or operator-specific tunnel IDs here.
    """
    url = server_url or f"https://mcp.example.invalid{DEFAULT_PATH}"
    openai_ext: dict[str, object] = {
        "auth": {"type": CHATGPT_AUTH_TYPE},
        "auth_model": CHATGPT_AUTH_MODEL,
        "preferred_connection": (
            "secure_mcp_tunnel" if use_secure_mcp_tunnel else "stable_https"
        ),
        "local_stdio_command": STDIO_COMMAND,
        "local_http_command": HTTP_COMMAND,
        "local_http_path": DEFAULT_PATH,
        "local_http_default_port": DEFAULT_PORT,
        "mcp_http_schema": MCP_HTTP_SCHEMA,
        "read_only": True,
        "public_directory_submission": False,
    }
    return {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        "mcpServers": {
            MCP_SERVER_NAME: {
                "type": "http",
                "url": url,
                "extensions": {
                    "com.openai": openai_ext,
                },
            }
        },
    }


def chatgpt_plugin_manifest() -> dict[str, object]:
    """Root ``plugin.json`` identity for the ChatGPT Agent Brain plugin package."""
    return {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "agent-brain",
        "version": __version__,
        "description": (
            "Agent Brain cdb_context — ChatGPT plugin surface over shared remote MCP "
            "(Secure MCP Tunnel or HTTPS /mcp)."
        ),
        "author": {"name": "Jannek Büngener"},
        "homepage": "https://github.com/jannekbuengener/agent-brain",
        "repository": "https://github.com/jannekbuengener/agent-brain",
        "license": "SEE REPOSITORY",
        "keywords": [
            "agent-brain",
            "cdb_context",
            "mcp",
            "chatgpt",
            "context",
            "evidence",
        ],
        "extensions": {
            "com.openai": {
                "display_name": "Agent Brain",
                "capability_contract_schema": CAPABILITY_CONTRACT_SCHEMA,
                "agent_brain_version": __version__,
                "auth_model": CHATGPT_AUTH_MODEL,
                "ui": False,
                "public_directory_submission": False,
            }
        },
    }


def foundation_metadata() -> dict[str, object]:
    return {
        "product_name": "Agent Brain",
        "mcp_server_name": MCP_SERVER_NAME,
        "mcp_server_schema": MCP_SERVER_SCHEMA,
        "mcp_http_schema": MCP_HTTP_SCHEMA,
        "capability_contract_schema": CAPABILITY_CONTRACT_SCHEMA,
        "agent_brain_version": __version__,
        "pin": f"agent-brain=={__version__}",
        "git_tag": f"v{__version__}",
        "read_only": True,
        "chatgpt_auth_model": CHATGPT_AUTH_MODEL,
    }


__all__ = [
    "CHATGPT_AUTH_MODEL",
    "CHATGPT_AUTH_TYPE",
    "HTTP_ARGS",
    "HTTP_COMMAND",
    "HTTP_MODULE_FALLBACK_ARGS",
    "MODULE_FALLBACK_ARGS",
    "MODULE_FALLBACK_COMMAND",
    "STDIO_ARGS",
    "STDIO_COMMAND",
    "chatgpt_plugin_manifest",
    "chatgpt_remote_mcp_json",
    "claude_code_mcp_json",
    "cursor_agent_plugin_mcp_json",
    "foundation_metadata",
    "opencode_mcp_config",
    "shared_stdio_launch",
]
