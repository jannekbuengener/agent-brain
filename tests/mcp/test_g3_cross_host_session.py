"""G3 unit proof: Cursor-shaped session A → Claude-shaped session B uses recall."""

from __future__ import annotations

from pathlib import Path

from agent_brain.mcp.handoff_server import build_handoff_stdio_server
from agent_brain.mcp.handoff_transport import (
    HANDOFF_APPEND_TOOL,
    HANDOFF_RECALL_TOOL,
    HandoffMcpTransport,
)
from agent_brain.mcp.server import MCP_PROTOCOL_VERSION
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
            event_key=f"k-{len(self.events)}",
            repository_ref=kwargs["repository_ref"],
            agent_id=kwargs["agent_id"],
            task_ref=kwargs["task_ref"],
            status=kwargs["status"],
            summary=kwargs["summary"],
            next_step=kwargs["next_step"],
            source_ref=kwargs["source_ref"],
            created_at=f"2026-11-03T00:00:0{len(self.events)}.000000Z",
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


def _call(server, msg_id: int, method: str, params: dict | None = None) -> dict:
    message: dict = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        message["params"] = params
    response = server.handle_message(message)
    assert response is not None
    return response


def test_cursor_session_then_claude_session_continues(tmp_path: Path) -> None:
    store = HandoffCredentialStore(
        pepper=load_or_create_pepper(tmp_path),
        denylist=RevokeDenylist(tmp_path / "deny.jsonl"),
        grants_path=tmp_path / "grants.json",
    )
    _, token_sb = store.enroll(
        consumer_id="sample-brain",
        repository_ref="jannekbuengener/sample-brain",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    _, token_sec = store.enroll(
        consumer_id="security-business",
        repository_ref="jannekbuengener/security-business",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    gateway = HandoffGateway(store, _MemoryJournal())  # type: ignore[arg-type]

    cursor = build_handoff_stdio_server(
        HandoffMcpTransport(gateway, token_provider=lambda: token_sb)
    )
    _call(
        cursor,
        1,
        "initialize",
        {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "cursor", "version": "0"},
        },
    )
    written = _call(
        cursor,
        2,
        "tools/call",
        {
            "name": HANDOFF_APPEND_TOOL,
            "arguments": {
                "repository_ref": "jannekbuengener/sample-brain",
                "agent_id": "cursor",
                "task_ref": "issue:1364",
                "status": "in_progress",
                "summary": "Cursor stored work; Claude must continue.",
                "next_step": "Recall and append continuation.",
                "source_ref": "test",
                "idempotency_key": "cursor-a",
            },
        },
    )
    assert written["result"]["isError"] is False

    claude = build_handoff_stdio_server(
        HandoffMcpTransport(gateway, token_provider=lambda: token_sb)
    )
    _call(
        claude,
        1,
        "initialize",
        {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "claude-code", "version": "0"},
        },
    )
    recalled = _call(
        claude,
        2,
        "tools/call",
        {
            "name": HANDOFF_RECALL_TOOL,
            "arguments": {
                "repository_ref": "jannekbuengener/sample-brain",
                "task_ref": "issue:1364",
            },
        },
    )
    assert recalled["result"]["isError"] is False
    event = recalled["result"]["structuredContent"]["events"][0]
    assert event["next_step"] == "Recall and append continuation."
    continued = _call(
        claude,
        3,
        "tools/call",
        {
            "name": HANDOFF_APPEND_TOOL,
            "arguments": {
                "repository_ref": "jannekbuengener/sample-brain",
                "agent_id": "claude-code",
                "task_ref": "issue:1364",
                "status": "completed",
                "summary": f"Used: {event['next_step']}",
                "next_step": "done",
                "source_ref": "test",
                "idempotency_key": "claude-b",
            },
        },
    )
    assert continued["result"]["isError"] is False

    foreign = build_handoff_stdio_server(
        HandoffMcpTransport(gateway, token_provider=lambda: token_sec)
    )
    _call(
        foreign,
        1,
        "initialize",
        {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "cursor", "version": "0"},
        },
    )
    denied = _call(
        foreign,
        2,
        "tools/call",
        {
            "name": HANDOFF_RECALL_TOOL,
            "arguments": {"repository_ref": "jannekbuengener/sample-brain"},
        },
    )
    assert denied["result"]["structuredContent"]["code"] == "FORBIDDEN"
