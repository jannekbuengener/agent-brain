"""Standalone CLI transport tests (#12)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import agent_brain
from agent_brain.cli.main import main
from agent_brain.protocol import ProtocolErrorCode, exit_code_for


def test_cli_version_matches_package(capsys) -> None:
    code = main(["version", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["agent_brain_version"] == agent_brain.__version__
    assert payload["agent_brain_version"] == agent_brain.__version__


def test_cli_health_and_capabilities_json(capsys) -> None:
    assert main(["health", "--json"]) == 0
    health = json.loads(capsys.readouterr().out)
    assert health["data"]["overall"] == "degraded"

    assert main(["capabilities", "--json"]) == 0
    caps = json.loads(capsys.readouterr().out)
    states = {item["capability"]: item["state"] for item in caps["data"]["capabilities"]}
    assert states["memory_read"] == "unavailable"
    assert states["context_read"] == "available"


def test_cli_invoke_parity_with_protocol(capsys) -> None:
    code = main(["invoke", "--operation", "evidence", "--payload", '{"scope":"repo:x"}'])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert "trust_summary" in payload["data"]


def test_cli_invalid_scope_exit_code(capsys) -> None:
    code = main(["invoke", "--operation", "evidence", "--payload", "{}"])
    assert code == exit_code_for(ProtocolErrorCode.INVALID_SCOPE)
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_scope"


def test_cli_memory_unavailable_exit_code(capsys) -> None:
    code = main(
        [
            "memory-read",
            "--json",
            "--payload",
            json.dumps(
                {
                    "scope": {
                        "schema_version": "memory-scope/v1",
                        "kind": "tenant",
                        "tenant_id": "t1",
                    },
                    "as_of": "2026-10-31T12:00:00Z",
                }
            ),
        ]
    )
    assert code == exit_code_for(ProtocolErrorCode.CAPABILITY_UNAVAILABLE)


def test_cli_rejects_write_command(capsys) -> None:
    code = main(["invoke", "--operation", "remember", "--payload", "{}"])
    assert code == exit_code_for(ProtocolErrorCode.UNSUPPORTED_OPERATION)


def test_cli_module_entrypoint_version() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "agent_brain.cli", "version", "--json"],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2]),
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["data"]["agent_brain_version"] == agent_brain.__version__


def test_cli_no_claire_imports_in_surface() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "agent_brain"
    banned_imports = ("import claire", "from claire", "echtgeld")
    for path in (*(root / "cli").rglob("*.py"), *(root / "protocol").rglob("*.py")):
        text = path.read_text(encoding="utf-8").lower()
        for banned in banned_imports:
            assert banned not in text, f"{path} contains {banned!r}"
