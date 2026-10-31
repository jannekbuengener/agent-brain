"""Clean-env install + neutral protocol consumer smoke (#12)."""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from tests.distribution.conftest import DistributionEnv

PROTOCOL_CONSUMER_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "protocol"
    / "neutral_protocol_consumer"
)


@pytest.fixture
def protocol_distribution_env() -> DistributionEnv:
    return DistributionEnv(consumer_root=PROTOCOL_CONSUMER_ROOT)


def test_clean_env_cli_after_wheel_install(
    built_wheel: Path,
    protocol_distribution_env: DistributionEnv,
    package_version: str,
    tmp_path: Path,
) -> None:
    python = protocol_distribution_env.create_venv(tmp_path / "cli-venv")
    protocol_distribution_env.install_wheel(python, built_wheel)

    completed = subprocess.run(
        [str(python), "-m", "agent_brain.cli", "version", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["data"]["agent_brain_version"] == package_version

    # Console script entry point from packaging.
    script_probe = textwrap.dedent(
        """
        import json, shutil, subprocess
        exe = shutil.which("agent-brain")
        assert exe, "agent-brain console script missing"
        out = subprocess.check_output([exe, "version", "--json"], text=True)
        print(out)
        """
    )
    completed = subprocess.run(
        [str(python), "-c", script_probe],
        check=True,
        capture_output=True,
        text=True,
    )
    script_payload = json.loads(completed.stdout.strip())
    assert script_payload["data"]["agent_brain_version"] == package_version

    # No Claire dependency markers in installed protocol/cli surface.
    neutrality = textwrap.dedent(
        """
        import agent_brain.cli, agent_brain.protocol, pathlib, json
        roots = [
            pathlib.Path(agent_brain.cli.__file__).parent,
            pathlib.Path(agent_brain.protocol.__file__).parent,
        ]
        hits = []
        for root in roots:
            for path in root.rglob("*.py"):
                text = path.read_text(encoding="utf-8").lower()
                for banned in ("claire de binare", "echtgeld"):
                    if banned in text:
                        hits.append(f"{path}:{banned}")
        print(json.dumps({"hits": hits}))
        """
    )
    completed = subprocess.run(
        [str(python), "-c", neutrality],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout)["hits"] == []


def test_neutral_protocol_consumer_smoke(
    built_wheel: Path,
    protocol_distribution_env: DistributionEnv,
    package_version: str,
    tmp_path: Path,
) -> None:
    python = protocol_distribution_env.create_venv(tmp_path / "protocol-consumer-venv")
    protocol_distribution_env.install_wheel(python, built_wheel)
    protocol_distribution_env.install_path(python, PROTOCOL_CONSUMER_ROOT)

    script = textwrap.dedent(
        f"""
        from neutral_protocol_consumer import smoke
        import json
        print(json.dumps(smoke({package_version!r})))
        """
    )
    completed = subprocess.run(
        [str(python), "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout.strip())
    assert result["installed_version"] == package_version
    assert result["cli_version"] == package_version
    assert result["context_ok"] is True
    assert "context_read" in result["available_capabilities"]
    assert result["failure_code"] in {"capability_unavailable", "invalid_scope"}


def test_core_without_mcp_extra_in_wheel_metadata(built_wheel: Path) -> None:
    import zipfile

    with zipfile.ZipFile(built_wheel) as archive:
        metadata_name = next(
            name for name in archive.namelist() if name.endswith("METADATA")
        )
        metadata = archive.read(metadata_name).decode("utf-8").lower()
    assert "requires-dist: mcp" not in metadata
