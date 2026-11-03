"""G2: handoff tools on existing McpStdioServer without altering cdb_context MCP."""

from __future__ import annotations

from pathlib import Path

from agent_brain.capabilities import REQUIRED_CAPABILITY_NAMES
from agent_brain.mcp.handoff_server import build_handoff_stdio_server
from agent_brain.mcp.handoff_transport import (
    HANDOFF_APPEND_TOOL,
    HANDOFF_MCP_SCHEMA,
    HANDOFF_MCP_SERVER_NAME,
    HANDOFF_RECALL_TOOL,
    HandoffMcpTransport,
)
from agent_brain.mcp.host_configs import claude_code_handoff_mcp_json, cursor_handoff_mcp_json
from agent_brain.mcp.server import MCP_PROTOCOL_VERSION, McpStdioServer
from agent_brain.mcp.transport import mcp_tool_definitions
from agent_brain.memory.handoff import HandoffEvent
from agent_brain.memory.handoff_auth import (
    HandoffCredentialStore,
    HandoffOperation,
    RevokeDenylist,
    load_or_create_pepper,
)
from agent_brain.memory.handoff_gateway import HandoffGateway


class _MemoryJournal:
    def __init__(self) -> None:
        self.events: list[HandoffEvent] = []

    def append(self, **kwargs: str) -> HandoffEvent:
        event = HandoffEvent(
            event_key="mcp-k1",
            repository_ref=kwargs["repository_ref"],
            agent_id=kwargs["agent_id"],
            task_ref=kwargs["task_ref"],
            status=kwargs["status"],
            summary=kwargs["summary"],
            next_step=kwargs["next_step"],
            source_ref=kwargs["source_ref"],
            created_at="2026-11-03T00:00:00.000000Z",
        )
        self.events.append(event)
        return event

    def recall(self, *, repository_ref: str, task_ref: str | None = None, limit: int = 20):
        del limit
        return [
            event
            for event in self.events
            if event.repository_ref == repository_ref
            and (task_ref is None or event.task_ref == task_ref)
        ]


def _gateway(tmp_path: Path, token_out: list[str]) -> HandoffGateway:
    store = HandoffCredentialStore(
        pepper=load_or_create_pepper(tmp_path),
        denylist=RevokeDenylist(tmp_path / "deny.jsonl"),
        grants_path=tmp_path / "grants.json",
    )
    _, token = store.enroll(
        consumer_id="sample-brain",
        repository_ref="jannekbuengener/sample-brain",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    token_out.append(token)
    journal: object = _MemoryJournal()
    return HandoffGateway(store, journal)  # type: ignore[arg-type]


def test_readonly_tool_catalogue_unchanged() -> None:
    names = {tool["name"] for tool in mcp_tool_definitions()}
    assert names == set(REQUIRED_CAPABILITY_NAMES)
    assert HANDOFF_APPEND_TOOL not in names
    assert HANDOFF_RECALL_TOOL not in names


def test_default_stdio_server_still_read_only() -> None:
    server = McpStdioServer()
    init = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        }
    )
    assert init is not None
    assert init["result"]["_meta"]["read_only"] is True
    tools = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert tools is not None
    names = {tool["name"] for tool in tools["result"]["tools"]}
    assert names == set(REQUIRED_CAPABILITY_NAMES)


def test_handoff_stdio_append_recall_and_deny(tmp_path: Path) -> None:
    tokens: list[str] = []
    gateway = _gateway(tmp_path, tokens)
    transport = HandoffMcpTransport(gateway, token_provider=lambda: tokens[0])
    server = build_handoff_stdio_server(transport)

    init = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "cursor-test", "version": "0"},
            },
        }
    )
    assert init is not None
    assert init["result"]["serverInfo"]["name"] == HANDOFF_MCP_SERVER_NAME
    assert init["result"]["_meta"]["agent_brain_mcp_schema"] == HANDOFF_MCP_SCHEMA
    assert init["result"]["_meta"]["read_only"] is False

    listed = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert listed is not None
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert names == {HANDOFF_APPEND_TOOL, HANDOFF_RECALL_TOOL}

    append = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": HANDOFF_APPEND_TOOL,
                "arguments": {
                    "repository_ref": "jannekbuengener/sample-brain",
                    "agent_id": "cursor",
                    "task_ref": "issue:1364",
                    "status": "in_progress",
                    "summary": "G2 wiring started",
                    "next_step": "Verify recall in new session",
                    "source_ref": "github:issue:1364",
                    "idempotency_key": "g2-session-a",
                },
            },
        }
    )
    assert append is not None
    assert append["result"]["isError"] is False
    assert append["result"]["structuredContent"]["ok"] is True

    spoof = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": HANDOFF_RECALL_TOOL,
                "arguments": {"repository_ref": "jannekbuengener/security-business"},
            },
        }
    )
    assert spoof is not None
    assert spoof["result"]["isError"] is True
    assert spoof["result"]["structuredContent"]["code"] == "FORBIDDEN"

    recall = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": HANDOFF_RECALL_TOOL,
                "arguments": {
                    "repository_ref": "jannekbuengener/sample-brain",
                    "task_ref": "issue:1364",
                },
            },
        }
    )
    assert recall is not None
    assert recall["result"]["isError"] is False
    events = recall["result"]["structuredContent"]["events"]
    assert len(events) == 1
    assert events[0]["next_step"] == "Verify recall in new session"


def test_host_handoff_snippets_use_dedicated_entry() -> None:
    cursor = cursor_handoff_mcp_json()
    claude = claude_code_handoff_mcp_json()
    assert cursor["mcpServers"]["agent-brain-handoff"]["command"] == "agent-brain-mcp-handoff"
    assert claude["mcpServers"]["agent-brain-handoff"]["command"] == "agent-brain-mcp-handoff"
    assert "AGENT_BRAIN_HANDOFF_TOKEN" in cursor["mcpServers"]["agent-brain-handoff"]["env"]
