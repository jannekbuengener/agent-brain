"""G3 evidence harness: Cursor-shaped session A writes; Claude-shaped session B continues.

Uses the real grant-gated Handoff MCP transport (same tools hosts call). Does not
print plaintext tokens. Requires AGENT_BRAIN_SECRETS_PATH and a healthy local
SurrealDB on 127.0.0.1:8012. Opt-in: set AGENT_BRAIN_HANDOFF_G3_LIVE=1.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

from agent_brain.mcp.handoff_server import build_handoff_stdio_server
from agent_brain.mcp.handoff_transport import (
    HANDOFF_APPEND_TOOL,
    HANDOFF_RECALL_TOOL,
    HandoffMcpTransport,
)
from agent_brain.mcp.host_configs import claude_code_handoff_mcp_json, cursor_handoff_mcp_json
from agent_brain.mcp.server import MCP_PROTOCOL_VERSION
from agent_brain.memory.handoff import SurrealHandoffJournal, load_local_authorization
from agent_brain.memory.handoff_auth import HandoffCredentialStore, HandoffOperation
from agent_brain.memory.handoff_gateway import HandoffGateway
from agent_brain.surrealdb.config import SurrealDbReadSettings


def _call(server, *, msg_id: int, method: str, params: dict | None = None) -> dict:
    message = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        message["params"] = params
    response = server.handle_message(message)
    assert response is not None
    return response


def _session(label: str, token: str, gateway: HandoffGateway):
    transport = HandoffMcpTransport(gateway, token_provider=lambda: token)
    server = build_handoff_stdio_server(transport)
    init = _call(
        server,
        msg_id=1,
        method="initialize",
        params={
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": label, "version": "g3-e2e"},
        },
    )
    return server, init


def main() -> int:
    if os.environ.get("AGENT_BRAIN_HANDOFF_G3_LIVE") != "1":
        print(json.dumps({"ok": False, "error": "set AGENT_BRAIN_HANDOFF_G3_LIVE=1"}, ensure_ascii=False))
        return 2

    store = HandoffCredentialStore.for_secrets_dir()
    grant_a, token_a = store.enroll(
        consumer_id="sample-brain-g3",
        repository_ref="jannekbuengener/sample-brain",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    grant_b, token_b = store.enroll(
        consumer_id="security-business-g3",
        repository_ref="jannekbuengener/security-business",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    journal = SurrealHandoffJournal(
        SurrealDbReadSettings(
            endpoint="http://127.0.0.1:8012",
            namespace="agent_brain",
            database="shared_memory",
            expected_server_version_prefix="surrealdb-3.0",
            timeout_seconds=5.0,
        ),
        authorization=load_local_authorization(),
        initialize=True,
    )
    gateway = HandoffGateway(store, journal)
    task = f"g3-e2e:{uuid.uuid4().hex[:12]}"
    key = f"{task}:cursor-session-a"

    # Host A — Cursor-shaped new session
    cursor_server, cursor_init = _session("cursor", token_a, gateway)
    assert cursor_init["result"]["serverInfo"]["name"] == "agent-brain-handoff"
    append = _call(
        cursor_server,
        msg_id=2,
        method="tools/call",
        params={
            "name": HANDOFF_APPEND_TOOL,
            "arguments": {
                "repository_ref": "jannekbuengener/sample-brain",
                "agent_id": "cursor",
                "task_ref": task,
                "status": "in_progress",
                "summary": "Cursor session stored G3 pilot state; Claude must continue.",
                "next_step": "Claude Code recalls this event and appends continuation.",
                "source_ref": "github:agent-brain#96",
                "idempotency_key": key,
            },
        },
    )
    assert append["result"]["isError"] is False, append

    # Host B — Claude Code-shaped NEW session (new server instance)
    claude_server, claude_init = _session("claude-code", token_a, gateway)
    assert claude_init["result"]["_meta"]["read_only"] is False
    recall = _call(
        claude_server,
        msg_id=2,
        method="tools/call",
        params={
            "name": HANDOFF_RECALL_TOOL,
            "arguments": {
                "repository_ref": "jannekbuengener/sample-brain",
                "task_ref": task,
            },
        },
    )
    assert recall["result"]["isError"] is False, recall
    events = recall["result"]["structuredContent"]["events"]
    assert len(events) == 1
    assert "Claude must continue" in events[0]["summary"]
    # B uses the recalled next_step
    used_next = events[0]["next_step"]
    cont = _call(
        claude_server,
        msg_id=3,
        method="tools/call",
        params={
            "name": HANDOFF_APPEND_TOOL,
            "arguments": {
                "repository_ref": "jannekbuengener/sample-brain",
                "agent_id": "claude-code",
                "task_ref": task,
                "status": "completed",
                "summary": f"Used prior next_step: {used_next}",
                "next_step": "Close G3 evidence; deny cross-tenant.",
                "source_ref": "github:agent-brain#96",
                "idempotency_key": f"{task}:claude-session-b",
            },
        },
    )
    assert cont["result"]["isError"] is False, cont

    # Cross-tenant denial with security-business token against sample-brain scope
    foreign_server, _ = _session("cursor-foreign", token_b, gateway)
    denied = _call(
        foreign_server,
        msg_id=2,
        method="tools/call",
        params={
            "name": HANDOFF_RECALL_TOOL,
            "arguments": {"repository_ref": "jannekbuengener/sample-brain"},
        },
    )
    assert denied["result"]["isError"] is True
    assert denied["result"]["structuredContent"]["code"] == "FORBIDDEN"

    # Revoke cleanup for ephemeral G3 grants (denylist keeps hashes dead)
    store.revoke(grant_a.grant_id, reason="g3-e2e-cleanup")
    store.revoke(grant_b.grant_id, reason="g3-e2e-cleanup")

    evidence = {
        "ok": True,
        "gate": "G3_CROSS_REPO_CROSS_HOST_PROVEN_PARTIAL",
        "hosts": {
            "cursor_snippet_command": cursor_handoff_mcp_json()["mcpServers"]["agent-brain-handoff"][
                "command"
            ],
            "claude_snippet_command": claude_code_handoff_mcp_json()["mcpServers"][
                "agent-brain-handoff"
            ]["command"],
            "session_a": "cursor",
            "session_b": "claude-code",
        },
        "task_ref": task,
        "sample_brain_events": 2,
        "cross_tenant_denied": True,
        "note": "Plaintext tokens never written to this evidence blob.",
    }
    out = Path(os.environ.get("AGENT_BRAIN_G3_EVIDENCE_PATH", "g3_cross_host_evidence.json"))
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - operator script fail-closed
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
