"""Shared MCP stdio transport tests (#73 Goal 2)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from agent_brain import __version__
from agent_brain.capabilities import (
    AGENT_BRAIN_HEALTH,
    CAPABILITY_CONTRACT_SCHEMA,
    CDB_CONTEXT_BRIEFING,
    CDB_CONTEXT_EVIDENCE,
    CDB_CONTEXT_REQUIRED_READS,
    CDB_CONTEXT_SEARCH,
    REQUIRED_CAPABILITY_NAMES,
)
from agent_brain.mcp.server import MCP_PROTOCOL_VERSION, MCP_SERVER_NAME, McpStdioServer
from agent_brain.mcp.transport import CapabilityMcpTransport
from agent_brain.protocol.errors import ProtocolErrorCode
from tests.capabilities.test_host_contract_suite import run_host_contract_suite


@pytest.fixture
def server() -> McpStdioServer:
    return McpStdioServer()


def test_initialize_exposes_version_and_readonly_meta(server: McpStdioServer) -> None:
    response = server.handle_message(
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
    assert response is not None
    result = response["result"]
    assert isinstance(result, dict)
    assert result["serverInfo"]["name"] == MCP_SERVER_NAME
    assert result["serverInfo"]["version"] == __version__
    meta = result["_meta"]
    assert isinstance(meta, dict)
    assert meta["agent_brain_version"] == __version__
    assert meta["capability_contract_schema"] == CAPABILITY_CONTRACT_SCHEMA
    assert meta["read_only"] is True
    assert meta["requires_mcp_sdk"] is False
    assert meta["requires_private_operator_mcp"] is False
    assert meta["requires_claire_runtime"] is False


def test_tools_list_only_bounded_capabilities(server: McpStdioServer) -> None:
    response = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert response is not None
    tools = response["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert names == set(REQUIRED_CAPABILITY_NAMES)
    # No protocol-internal catalogue explosion.
    assert "context_read" not in names
    assert "memory_read" not in names
    assert "write" not in names


def test_tools_call_health_and_failure_semantics(server: McpStdioServer) -> None:
    ok = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": AGENT_BRAIN_HEALTH, "arguments": {}},
        }
    )
    assert ok is not None
    assert ok["result"]["isError"] is False
    body = ok["result"]["structuredContent"]
    assert body["ok"] is True
    assert body["agent_brain_version"] == __version__

    mismatch = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": AGENT_BRAIN_HEALTH,
                "arguments": {"contract_version": "agent-brain-cdb-context-capability/v99"},
            },
        }
    )
    assert mismatch is not None
    assert mismatch["result"]["isError"] is True
    err_body = mismatch["result"]["structuredContent"]
    assert err_body["ok"] is False
    assert err_body["error"]["code"] == ProtocolErrorCode.CONTRACT_VERSION_MISMATCH.value


def test_write_and_rejected_methods(server: McpStdioServer) -> None:
    write = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "remember", "arguments": {"text": "nope"}},
        }
    )
    assert write is not None
    assert write["result"]["isError"] is True
    assert (
        write["result"]["structuredContent"]["error"]["code"]
        == ProtocolErrorCode.UNSUPPORTED_OPERATION.value
    )

    rejected = server.handle_message(
        {"jsonrpc": "2.0", "id": 6, "method": "resources/list", "params": {}}
    )
    assert rejected is not None
    assert "error" in rejected


def test_host_contract_suite_via_transport() -> None:
    transport = CapabilityMcpTransport()

    def invoke(capability: str, payload=None, **kwargs):
        return transport.call_tool(capability, payload, **kwargs)

    run_host_contract_suite(invoke)


def _mcp_rpc(proc: subprocess.Popen[str], msg_id: int, method: str, params: dict | None = None) -> dict:
    payload = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        payload["params"] = params
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    assert line, f"no response for {method}"
    return json.loads(line)


@pytest.fixture
def mcp_process() -> Iterator[subprocess.Popen[str]]:
    proc = subprocess.Popen(
        [sys.executable, "-m", "agent_brain.mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    try:
        yield proc
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_subprocess_stdio_smoke(mcp_process: subprocess.Popen[str]) -> None:
    init = _mcp_rpc(
        mcp_process,
        1,
        "initialize",
        {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0"},
        },
    )
    assert init["result"]["serverInfo"]["version"] == __version__

    # notifications return no response
    assert mcp_process.stdin is not None
    mcp_process.stdin.write(
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
    )
    mcp_process.stdin.flush()

    tools = _mcp_rpc(mcp_process, 3, "tools/list")
    names = {t["name"] for t in tools["result"]["tools"]}
    assert names == set(REQUIRED_CAPABILITY_NAMES)

    for msg_id, tool, arguments in (
        (10, AGENT_BRAIN_HEALTH, {}),
        (11, CDB_CONTEXT_BRIEFING, {"task": "architecture overview"}),
        (
            12,
            CDB_CONTEXT_SEARCH,
            {
                "query": "repository canon",
                "scope": "repo_live",
                "records": [
                    {
                        "schema_version": "index-record/v1",
                        "record_id": "rec-1",
                        "record_type": "doc",
                        "source": {
                            "schema_version": "artifact-ref/v1",
                            "artifact_id": "art-1",
                            "source_id": "repo_live",
                            "source_path": "docs/meta/REPOSITORY_CANON.md",
                            "source_hash": "hash-1",
                        },
                        "content_hash": "content-1",
                        "attributes": {"title": "canon", "text": "repository canon"},
                    }
                ],
            },
        ),
        (13, CDB_CONTEXT_REQUIRED_READS, {"task": "architecture change"}),
        (14, CDB_CONTEXT_EVIDENCE, {"claim": "repo:authority"}),
    ):
        result = _mcp_rpc(
            mcp_process,
            msg_id,
            "tools/call",
            {"name": tool, "arguments": arguments},
        )
        body = result["result"]["structuredContent"]
        assert body["ok"] is True
        assert body["agent_brain_version"] == __version__

    failure = _mcp_rpc(
        mcp_process,
        20,
        "tools/call",
        {"name": CDB_CONTEXT_BRIEFING, "arguments": {}},
    )
    assert failure["result"]["isError"] is True
    assert failure["result"]["structuredContent"]["ok"] is False


def test_repo_has_no_user_absolute_paths_in_hosts() -> None:
    hosts = Path(__file__).resolve().parents[2] / "hosts"
    forbidden = ("C:\\Users\\janne", "C:/Users/janne", "D:\\Dev\\Workspaces", "D:/Dev/Workspaces")
    for path in hosts.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".pyc"}:
            continue
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} contains forbidden path {needle}"
