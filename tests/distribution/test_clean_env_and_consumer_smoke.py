from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_clean_environment_installs_exact_wheel_without_repo_path(
    built_wheel: Path,
    distribution_env,
    package_version: str,
    tmp_path: Path,
) -> None:
    python = distribution_env.create_venv(tmp_path / "clean-venv")
    distribution_env.install_wheel(python, built_wheel)

    script = """
import agent_brain, pathlib, json
module_path = pathlib.Path(agent_brain.__file__).resolve()
normalized = str(module_path).replace("\\\\", "/").lower()
print(json.dumps({
    "version": agent_brain.__version__,
    "module_path": str(module_path),
    "is_site_packages": "site-packages" in normalized,
}))
"""
    completed = subprocess.run(
        [str(python), "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload["version"] == package_version
    assert payload["is_site_packages"] is True
    assert "agent-brain-wt-17" not in payload["module_path"]


def test_neutral_consumer_smoke_against_pinned_wheel(
    built_wheel: Path,
    distribution_env,
    package_version: str,
    tmp_path: Path,
) -> None:
    python = distribution_env.create_venv(tmp_path / "consumer-venv")
    distribution_env.install_wheel(python, built_wheel)
    distribution_env.install_path(python, distribution_env.consumer_root)

    result = distribution_env.run_consumer_smoke(python, package_version)
    assert result["pinned_version"] == package_version
    assert result["installed_version"] == package_version
    assert result["compatible"] is True
    assert "agent_brain.distribution" in result["public_modules"]


def test_upgrade_and_rollback_with_exact_wheels(
    repo_root: Path,
    distribution_env,
    tmp_path: Path,
) -> None:
    dist_dir = tmp_path / "lifecycle-dist"
    wheel_010 = distribution_env.build_wheel(repo_root, dist_dir / "v010", version="0.1.0")
    wheel_011 = distribution_env.build_wheel(repo_root, dist_dir / "v011", version="0.1.1")

    python = distribution_env.create_venv(tmp_path / "lifecycle-venv")
    distribution_env.install_wheel(python, wheel_010)
    distribution_env.install_path(python, distribution_env.consumer_root)
    assert distribution_env.run_consumer_smoke(python, "0.1.0")["installed_version"] == "0.1.0"

    distribution_env.install_wheel(python, wheel_011)
    assert distribution_env.run_consumer_smoke(python, "0.1.1")["installed_version"] == "0.1.1"

    distribution_env.install_wheel(python, wheel_010)
    rolled = distribution_env.run_consumer_smoke(python, "0.1.0")
    assert rolled["installed_version"] == "0.1.0"
    assert rolled["compatible"] is True


def test_consumer_fixture_is_product_neutral(distribution_env) -> None:
    consumer_init = distribution_env.consumer_root / "src" / "neutral_brain_consumer" / "__init__.py"
    text = consumer_init.read_text(encoding="utf-8").lower()
    for forbidden in ("claire", "trading", "live-go", "echtgeld"):
        assert forbidden not in text

