"""Host packaging, purity, skill sync, and cross-host semantic parity (#73 Goal 2)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agent_brain import __version__
from agent_brain.capabilities import (
    AGENT_BRAIN_HEALTH,
    CDB_CONTEXT_BRIEFING,
    CDB_CONTEXT_EVIDENCE,
    CDB_CONTEXT_REQUIRED_READS,
    CDB_CONTEXT_SEARCH,
    REQUIRED_CAPABILITY_NAMES,
)
from agent_brain.mcp.host_configs import (
    CHATGPT_AUTH_MODEL,
    chatgpt_plugin_manifest,
    chatgpt_remote_mcp_json,
    claude_code_mcp_json,
    cursor_agent_plugin_mcp_json,
    foundation_metadata,
    opencode_mcp_config,
)
from agent_brain.mcp.server import McpStdioServer
from agent_brain.mcp.transport import CapabilityMcpTransport
from agent_brain.protocol.errors import ProtocolErrorCode
from tests.capabilities.test_host_contract_suite import (
    _minimal_record,
    run_host_contract_suite,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
HOSTS = REPO_ROOT / "hosts"
CANONICAL_SKILL = HOSTS / "shared" / "skills" / "agent-brain-cdb-context" / "SKILL.md"
DISTRIBUTED_SKILLS = (
    HOSTS / "claude-code" / "plugins" / "agent-brain" / "skills" / "agent-brain-cdb-context" / "SKILL.md",
    HOSTS / "cursor" / "agent-brain" / "skills" / "agent-brain-cdb-context" / "SKILL.md",
    HOSTS / "opencode" / "skills" / "agent-brain-cdb-context" / "SKILL.md",
    HOSTS / "chatgpt" / "agent-brain" / "skills" / "agent-brain-cdb-context" / "SKILL.md",
)

FORBIDDEN_IMPORT_MARKERS = (
    "agent_brain.context",
    "agent_brain.retrieval",
    "agent_brain.evidence",
    "Claire_de_Binare",
    "claire_de_binare",
)
ABS_PATH_PATTERNS = (
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"C:/Users/", re.IGNORECASE),
    re.compile(r"D:\\Dev\\", re.IGNORECASE),
    re.compile(r"D:/Dev/", re.IGNORECASE),
)

# Shared realistic CDB task for cross-host semantic parity.
SHARED_CDB_TASK = {
    "task": "Änderung am CDB Context-/Architecture-Bereich: Required Reads und belegter Context",
}


def _semantic_fields(body: dict) -> dict:
    """Compare capability-relevant fields; ignore host envelope noise."""
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    return {
        "ok": body.get("ok"),
        "operation": body.get("operation"),
        "error_code": (body.get("error") or {}).get("code") if body.get("error") else None,
        "capability": data.get("capability"),
        "limitations": list(body.get("limitations") or ()),
        "required_read_paths": sorted(
            item.get("path")
            for item in (data.get("required_reads") or [])
            if isinstance(item, dict)
        ),
        "evidence_state": data.get("evidence_state"),
        "confirmed": data.get("confirmed"),
        "profile_identity": (data.get("profile") or {}).get("repository_identity")
        if isinstance(data.get("profile"), dict)
        else None,
        "agent_brain_version": body.get("agent_brain_version"),
    }


def _invoke_via_host_label(host: str, capability: str, arguments: dict) -> dict:
    """Each host label uses the same shared MCP transport (parity of semantics)."""
    del host  # packaging differs; executed operations must not.
    server = McpStdioServer(transport=CapabilityMcpTransport())
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": capability, "arguments": arguments},
        }
    )
    assert response is not None
    return response["result"]["structuredContent"]


@pytest.mark.parametrize("host", ["claude-code", "cursor", "opencode", "chatgpt"])
def test_host_contract_suite_binding(host: str) -> None:
    assert host in {"claude-code", "cursor", "opencode", "chatgpt"}
    transport = CapabilityMcpTransport()

    def invoke(capability: str, payload=None, **kwargs):
        return transport.call_tool(capability, payload, **kwargs)

    run_host_contract_suite(invoke)


def test_skill_copies_match_canonical() -> None:
    canonical = CANONICAL_SKILL.read_bytes()
    assert canonical, "canonical skill missing"
    for path in DISTRIBUTED_SKILLS:
        assert path.is_file(), path
        assert path.read_bytes() == canonical, f"skill drift at {path}"


def test_host_manifests_and_mcp_configs() -> None:
    claude_plugin = HOSTS / "claude-code" / "plugins" / "agent-brain" / ".claude-plugin" / "plugin.json"
    claude_mcp = HOSTS / "claude-code" / "plugins" / "agent-brain" / ".mcp.json"
    cursor_plugin = HOSTS / "cursor" / "agent-brain" / "plugin.json"
    cursor_mcp = HOSTS / "cursor" / "agent-brain" / "mcp.json"
    opencode_mcp = HOSTS / "opencode" / "opencode.agent-brain.mcp.example.json"
    chatgpt_plugin = HOSTS / "chatgpt" / "agent-brain" / "plugin.json"
    chatgpt_mcp = HOSTS / "chatgpt" / "agent-brain" / "mcp.json"

    for path in (
        claude_plugin,
        claude_mcp,
        cursor_plugin,
        cursor_mcp,
        opencode_mcp,
        chatgpt_plugin,
        chatgpt_mcp,
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    assert json.loads(claude_mcp.read_text(encoding="utf-8")) == claude_code_mcp_json()
    assert json.loads(cursor_mcp.read_text(encoding="utf-8")) == cursor_agent_plugin_mcp_json()
    example = json.loads(opencode_mcp.read_text(encoding="utf-8"))
    assert example["mcp"] == opencode_mcp_config()["mcp"]
    assert json.loads(chatgpt_plugin.read_text(encoding="utf-8")) == chatgpt_plugin_manifest()
    assert json.loads(chatgpt_mcp.read_text(encoding="utf-8")) == chatgpt_remote_mcp_json()

    cursor_manifest = json.loads(cursor_plugin.read_text(encoding="utf-8"))
    assert cursor_manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert cursor_manifest["name"] == "agent-brain"

    chatgpt_manifest = json.loads(chatgpt_plugin.read_text(encoding="utf-8"))
    assert chatgpt_manifest["version"] == __version__
    assert chatgpt_manifest["extensions"]["com.openai"]["auth_model"] == CHATGPT_AUTH_MODEL
    assert chatgpt_manifest["extensions"]["com.openai"]["ui"] is False
    openai_ext = json.loads(chatgpt_mcp.read_text(encoding="utf-8"))["mcpServers"]["agent-brain"][
        "extensions"
    ]["com.openai"]
    assert openai_ext["auth"]["type"] == "none"
    assert openai_ext["preferred_connection"] == "secure_mcp_tunnel"
    assert "sk-" not in json.dumps(openai_ext)


def test_no_absolute_user_paths_and_host_adapter_purity() -> None:
    for path in HOSTS.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".pyc"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in ABS_PATH_PATTERNS:
            assert not pattern.search(text), f"{path} has absolute user path"
        # Host packages are packaging-only: no Python capability imports.
        if path.suffix.lower() in {".py", ".ts", ".js", ".mjs", ".cjs"}:
            pytest.fail(f"host adapter must stay packaging-only, found code file: {path}")
        for marker in FORBIDDEN_IMPORT_MARKERS:
            # README may mention Claire as evidence source — allow docs prose in README/SKILL.
            if path.name.upper() == "SKILL.MD" or path.name.upper() == "README.MD":
                continue
            assert marker not in text, f"{path} contains forbidden marker {marker}"


def test_foundation_metadata_pins_exact_version() -> None:
    meta = foundation_metadata()
    assert meta["agent_brain_version"] == __version__
    assert meta["pin"] == f"agent-brain=={__version__}"
    assert "latest" not in str(meta).lower()
    assert "main" not in meta["pin"]


@pytest.mark.parametrize(
    ("capability", "arguments"),
    [
        (AGENT_BRAIN_HEALTH, {}),
        (CDB_CONTEXT_BRIEFING, SHARED_CDB_TASK),
        (
            CDB_CONTEXT_SEARCH,
            {
                "query": "context architecture required reads",
                "scope": "repo_live",
                "records": [_minimal_record()],
            },
        ),
        (CDB_CONTEXT_REQUIRED_READS, SHARED_CDB_TASK),
        (CDB_CONTEXT_EVIDENCE, {"claim": "repo:authority", "topic": "architecture"}),
    ],
)
def test_cross_host_semantic_parity(capability: str, arguments: dict) -> None:
    # Goal 3 adds ChatGPT as another transport consumer of the same semantics.
    # Final four-host closeout remains Goal 4; Goal 3 still requires ChatGPT parity
    # against the canonical contract.
    results = {
        host: _semantic_fields(_invoke_via_host_label(host, capability, arguments))
        for host in ("claude-code", "cursor", "opencode", "chatgpt")
    }
    baseline = results["claude-code"]
    assert results["cursor"] == baseline
    assert results["opencode"] == baseline
    assert results["chatgpt"] == baseline
    assert baseline["agent_brain_version"] == __version__


def test_cross_host_error_parity() -> None:
    cases = [
        (CDB_CONTEXT_BRIEFING, {}, ProtocolErrorCode.INVALID_INPUT),
        (CDB_CONTEXT_SEARCH, {"query": "x", "scope": "   "}, ProtocolErrorCode.INVALID_SCOPE),
        (
            AGENT_BRAIN_HEALTH,
            {"contract_version": "agent-brain-cdb-context-capability/v99"},
            ProtocolErrorCode.CONTRACT_VERSION_MISMATCH,
        ),
        ("remember", {"text": "x"}, ProtocolErrorCode.UNSUPPORTED_OPERATION),
    ]
    for capability, arguments, expected in cases:
        coded = {
            host: _invoke_via_host_label(host, capability, arguments)["error"]["code"]
            for host in ("claude-code", "cursor", "opencode", "chatgpt")
        }
        assert set(coded.values()) == {expected.value}


def test_matrix_coverage_names() -> None:
    # Documented Pflicht-Testmatrix capabilities are exactly the shared required set.
    assert REQUIRED_CAPABILITY_NAMES == {
        AGENT_BRAIN_HEALTH,
        CDB_CONTEXT_BRIEFING,
        CDB_CONTEXT_SEARCH,
        CDB_CONTEXT_REQUIRED_READS,
        CDB_CONTEXT_EVIDENCE,
    }
