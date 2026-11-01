"""The pure briefing path must not depend on event-loop or backend availability."""

from __future__ import annotations

import asyncio
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest

from agent_brain.contracts.evidence import EvidenceRef
from agent_brain.mcp.server import McpStdioServer
from agent_brain.mcp.transport import CapabilityMcpTransport
from agent_brain.memory.in_memory import InMemoryKnowledgeStore, InMemoryMemoryStore
from agent_brain.memory.unavailable import UnavailableKnowledgeStore, UnavailableMemoryStore
from agent_brain.protocol.runtime import ProtocolRuntime

TASK = "Agent Brain Multi-Surface Plugin / GitHub Issue #73 / ChatGPT Integration"


class BlockingBackend:
    async def health(self):
        await asyncio.Event().wait()

    async def query(self, *args, **kwargs):
        await asyncio.Event().wait()

    async def recall(self, *args, **kwargs):
        await asyncio.Event().wait()


@pytest.mark.parametrize("alias", ["task", "topic", "task_scope"])
@pytest.mark.parametrize("backend_case", ["all_unavailable", "knowledge_unavailable",
                                         "memory_unavailable", "blocking", "healthy"])
def test_stdio_briefing_needs_neither_event_loop_nor_optional_backends(
    monkeypatch, alias, backend_case,
):
    # A synchronous builder must never start the Windows socketpair self-pipe.
    # Fail immediately instead of leaving a test hung in socket.accept().
    new_loop = Mock(side_effect=AssertionError("event loop startup would block"))
    monkeypatch.setattr(asyncio.events, "new_event_loop", new_loop)
    runtime = ProtocolRuntime()
    if backend_case == "knowledge_unavailable":
        runtime.memory_store = InMemoryMemoryStore()
        runtime.knowledge_store = UnavailableKnowledgeStore()
    elif backend_case == "memory_unavailable":
        runtime.memory_store = UnavailableMemoryStore()
        runtime.knowledge_store = InMemoryKnowledgeStore()
    elif backend_case == "blocking":
        runtime.memory_store = BlockingBackend()
        runtime.knowledge_store = BlockingBackend()
    elif backend_case == "healthy":
        runtime.memory_store = InMemoryMemoryStore()
        runtime.knowledge_store = InMemoryKnowledgeStore()
    server = McpStdioServer(transport=CapabilityMcpTransport(runtime=runtime))
    result = server.handle_message({
        "jsonrpc": "2.0", "id": 73, "method": "tools/call",
        "params": {"name": "cdb_context.briefing", "arguments": {alias: TASK}},
    })
    body = result["result"]["structuredContent"]
    assert body["ok"] is True
    assert "partial_source_state" in body["limitations"]
    assert "no_evidence" in body["limitations"]
    assert body["data"]["briefing"]["context_package_ref"] is None
    assert TASK in body["data"]["briefing"]["scope_summary"]
    new_loop.assert_not_called()


def test_stdio_subprocess_returns_when_socketpair_would_block():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    code = (
        "import socket, time; from agent_brain.mcp.server import serve_stdio; "
        "socket.socketpair = lambda *a, **k: time.sleep(60); "
        "print('READY', flush=True); serve_stdio()"
    )
    message = {
        "jsonrpc": "2.0", "id": 73, "method": "tools/call",
        "params": {"name": "cdb_context.briefing", "arguments": {"task": TASK}},
    }
    process = subprocess.Popen(
        [sys.executable, "-c", code], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    ready = queue.Queue()
    reader = threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True)
    reader.start()
    try:
        # Interpreter/import startup is separate from the tool-call budget.
        assert ready.get(timeout=30) == "READY\n"
        reader.join(timeout=1)
        stdout, stderr = process.communicate(json.dumps(message) + "\n", timeout=5)
        assert process.returncode == 0, stderr
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
    body = json.loads(stdout)["result"]["structuredContent"]
    assert body["ok"] is True
    assert body["limitations"] == ["partial_source_state", "no_evidence"]


@pytest.mark.parametrize("payload", [
    {"mode": "briefing", "task_id": "healthy", "task_scope": TASK},
    {"mode": "briefing", "task_id": "healthy", "task_scope": TASK, "evidence_refs": [{
        "schema_version": "evidence-ref/v1", "evidence_id": "evidence-neutral",
        "evidence_type": "test-result", "source_refs": ["repo_live"],
        "artifact_refs": ["artifact-neutral"], "summary": "Neutral evidence",
    }]},
    {"mode": "briefing"},
    {"mode": "briefing", "task_id": "invalid", "task_scope": TASK,
     "requested_depth": "invalid"},
    {"mode": "package", "target_scope": "neutral", "artifacts": []},
])
def test_context_sync_async_response_parity(payload):
    from agent_brain.protocol.gateway import ProtocolGateway
    from agent_brain.protocol.models import ProtocolRequest

    gateway = ProtocolGateway()
    request = ProtocolRequest("context_read", payload, request_id="correlation-73")
    sync = gateway.invoke_sync(request)
    asynchronous = asyncio.run(gateway.invoke(request))
    assert sync.to_dict() == asynchronous.to_dict()
    assert sync.request_id == "correlation-73"
    if sync.ok and payload.get("evidence_refs"):
        assert sync.data["briefing"]["relevant_evidence"] == [
            EvidenceRef.from_dict(item).to_dict() for item in payload["evidence_refs"]
        ]
        assert "no_evidence" not in sync.limitations
