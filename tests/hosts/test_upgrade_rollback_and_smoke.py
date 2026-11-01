"""Host upgrade/rollback plans + fresh-host registration evidence (#73 Goal 2)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from agent_brain import __version__
from agent_brain.distribution import (
    ChangeKind,
    CompatibilityVerdict,
    build_rollback_plan,
    build_upgrade_plan,
    classify_surface_diff,
)
from agent_brain.mcp.host_configs import (
    claude_code_mcp_json,
    cursor_agent_plugin_mcp_json,
    opencode_mcp_config,
)
from agent_brain.mcp.server import McpStdioServer
from agent_brain.mcp.transport import CapabilityMcpTransport

REPO_ROOT = Path(__file__).resolve().parents[2]
PREVIOUS_FOUNDATION = "0.3.1"
CURRENT = __version__


def test_upgrade_and_rollback_plans_for_host_pins() -> None:
    compatibility = classify_surface_diff(
        removed=set(),
        added={"agent_brain.mcp:serve_http"},
    )
    assert compatibility.verdict is CompatibilityVerdict.COMPATIBLE
    assert compatibility.kind is ChangeKind.ADDITIVE

    upgrade = build_upgrade_plan(
        current_version=PREVIOUS_FOUNDATION,
        target_version=CURRENT,
        compatibility=compatibility,
    )
    assert upgrade.target_requirement == f"agent-brain=={CURRENT}"
    assert "latest" not in upgrade.target_requirement

    rollback = build_rollback_plan(failed_version=CURRENT, previous_version=PREVIOUS_FOUNDATION)
    assert rollback.previous_requirement == f"agent-brain=={PREVIOUS_FOUNDATION}"
    assert rollback.steps[2].requirement == f"agent-brain=={PREVIOUS_FOUNDATION}"


def test_fresh_host_config_isolation_no_jannek_paths(tmp_path: Path) -> None:
    """Fresh temp home/config dirs get portable MCP registration only."""
    home = tmp_path / "home"
    home.mkdir()
    configs = {
        "claude.mcp.json": claude_code_mcp_json(),
        "cursor.mcp.json": cursor_agent_plugin_mcp_json(),
        "opencode.json": {**opencode_mcp_config(), "$schema": "https://opencode.ai/config.json"},
    }
    for name, payload in configs.items():
        path = home / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        text = path.read_text(encoding="utf-8")
        assert "Users\\janne" not in text
        assert "Users/janne" not in text
        assert "D:\\Dev" not in text
        assert "D:/Dev" not in text
        assert "agent-brain-mcp" in text
        assert "Users\\janne" not in json.dumps(payload)


def test_mcp_transport_survives_isolated_cwd(tmp_path: Path) -> None:
    """Fresh host must not require the agent-brain source checkout as CWD."""
    server = McpStdioServer(transport=CapabilityMcpTransport())
    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "agent_brain.health", "arguments": {}},
            }
        )
    finally:
        os.chdir(old)
    assert response is not None
    assert response["result"]["structuredContent"]["ok"] is True
    assert response["result"]["structuredContent"]["agent_brain_version"] == CURRENT


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def test_claude_plugin_validate_smoke() -> None:
    claude = shutil.which("claude")
    if not claude:
        pytest.skip("claude CLI unavailable")
    plugin = REPO_ROOT / "hosts" / "claude-code" / "plugins" / "agent-brain"
    marketplace = REPO_ROOT / "hosts" / "claude-code"
    plugin_result = _run([claude, "plugin", "validate", str(plugin)])
    market_result = _run([claude, "plugin", "validate", str(marketplace)])
    assert plugin_result.returncode == 0, plugin_result.stdout + plugin_result.stderr
    assert market_result.returncode == 0, market_result.stdout + market_result.stderr


def test_opencode_mcp_config_list_smoke(tmp_path: Path) -> None:
    opencode = shutil.which("opencode")
    if not opencode:
        pytest.skip("opencode CLI unavailable")
    if not shutil.which("agent-brain-mcp"):
        pytest.skip("agent-brain-mcp not on PATH")
    config = {
        "$schema": "https://opencode.ai/config.json",
        **opencode_mcp_config(),
    }
    config_path = tmp_path / "opencode.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    # Prefer OPENCODE_CONFIG: bare tmp cwd discovery is flaky across hosts.
    env = {**os.environ, "OPENCODE_CONFIG": str(config_path)}
    combined = ""
    for attempt in range(3):
        result = _run(
            [opencode, "mcp", "list", "--print-logs", "--log-level", "INFO"],
            cwd=tmp_path,
            env=env,
        )
        combined = (result.stdout or "") + (result.stderr or "")
        lines = combined.splitlines()
        log_ok = any(
            "key=agent-brain" in line and "successfully created client" in line for line in lines
        )
        # UI row may include other failed servers; require agent-brain itself connected.
        agent_row_ok = any(
            "agent-brain" in "\n".join(lines[idx : idx + 3]).lower()
            and "connected" in "\n".join(lines[idx : idx + 3]).lower()
            and "failed" not in "\n".join(lines[idx : idx + 3]).lower()
            for idx, line in enumerate(lines)
            if "agent-brain" in line.lower() and "key=agent-brain" not in line
        )
        if log_ok or agent_row_ok:
            return
        if attempt < 2:
            time.sleep(2)
    pytest.fail(f"OpenCode did not connect agent-brain after retries:\n{combined}")


def test_cursor_agent_plugin_files_present_for_host_smoke() -> None:
    """Cursor has no stable CLI validator; packaging evidence is the Agent Plugin tree."""
    root = REPO_ROOT / "hosts" / "cursor" / "agent-brain"
    assert (root / "plugin.json").is_file()
    assert (root / "mcp.json").is_file()
    assert (root / "skills" / "agent-brain-cdb-context" / "SKILL.md").is_file()
    manifest = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["$schema"].startswith("https://agent-plugins.org/schemas/")


def test_chatgpt_agent_plugin_files_present_for_host_smoke() -> None:
    """ChatGPT packaging evidence: plugin identity + remote MCP declaration + skill."""
    root = REPO_ROOT / "hosts" / "chatgpt" / "agent-brain"
    assert (root / "plugin.json").is_file()
    assert (root / "mcp.json").is_file()
    assert (root / "skills" / "agent-brain-cdb-context" / "SKILL.md").is_file()
    manifest = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    mcp = json.loads((root / "mcp.json").read_text(encoding="utf-8"))
    assert manifest["version"] == CURRENT
    assert mcp["mcpServers"]["agent-brain"]["type"] == "http"
    assert "/mcp" in mcp["mcpServers"]["agent-brain"]["url"]
    assert "sk-" not in json.dumps(mcp)


def test_console_script_entrypoint_resolves() -> None:
    # After editable install, module entry works without source CWD.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from agent_brain.mcp.server import main; import inspect; assert callable(main); "
                "from agent_brain.mcp.http import main as http_main; assert callable(http_main)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
