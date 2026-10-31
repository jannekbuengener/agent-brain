"""Distribution-test helpers for isolated wheel builds and consumer smokes."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import tomllib
import venv
from dataclasses import dataclass
from pathlib import Path

import pytest

CONSUMER_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "distribution" / "neutral_consumer"
)


def _run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"command failed: {command}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def _python_in(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


@dataclass(frozen=True, slots=True)
class DistributionEnv:
    consumer_root: Path

    def create_venv(self, path: Path) -> Path:
        if path.exists():
            shutil.rmtree(path)
        builder = venv.EnvBuilder(with_pip=True, clear=True)
        builder.create(path)
        python = _python_in(path)
        _run([str(python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
        return python

    def build_wheel(
        self,
        source_root: Path,
        dist_dir: Path,
        *,
        version: str | None = None,
    ) -> Path:
        work = dist_dir / "src-tree"
        if work.exists():
            shutil.rmtree(work)
        shutil.copytree(
            source_root,
            work,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                ".pytest_cache",
                ".ruff_cache",
                "__pycache__",
                "*.egg-info",
                "dist",
                "build",
                ".mypy_cache",
            ),
        )
        if version is not None:
            pyproject = work / "pyproject.toml"
            text = pyproject.read_text(encoding="utf-8")
            updated: list[str] = []
            replaced = False
            for line in text.splitlines(keepends=True):
                if line.startswith("version = ") and not replaced:
                    updated.append(f'version = "{version}"\n')
                    replaced = True
                else:
                    updated.append(line)
            if not replaced:
                raise RuntimeError("failed to rewrite package version in pyproject.toml")
            pyproject.write_text("".join(updated), encoding="utf-8")
            builder = work / "src" / "agent_brain" / "knowledge" / "builder.py"
            builder_text = builder.read_text(encoding="utf-8")
            updated_builder, count = re.subn(
                r'DEFAULT_TOOL_VERSION = "agent-brain/[^"]+"',
                f'DEFAULT_TOOL_VERSION = "agent-brain/{version}"',
                builder_text,
                count=1,
            )
            if count != 1:
                raise RuntimeError("failed to rewrite DEFAULT_TOOL_VERSION in builder.py")
            builder.write_text(updated_builder, encoding="utf-8")

        out = dist_dir / "wheels"
        out.mkdir(parents=True, exist_ok=True)
        for existing in out.glob("agent_brain-*.whl"):
            existing.unlink()
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--wheel-dir",
                str(out),
                str(work),
            ]
        )
        wheels = sorted(out.glob("agent_brain-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected exactly one wheel, found {wheels}")
        return wheels[0]

    def install_wheel(self, python: Path, wheel: Path) -> None:
        _run([str(python), "-m", "pip", "install", "--force-reinstall", str(wheel)])

    def install_path(self, python: Path, path: Path) -> None:
        _run([str(python), "-m", "pip", "install", str(path)])

    def run_consumer_smoke(self, python: Path, pinned_version: str) -> dict[str, object]:
        script = textwrap.dedent(
            f"""
            from neutral_brain_consumer import smoke
            import json
            print(json.dumps(smoke({pinned_version!r})))
            """
        )
        completed = _run([str(python), "-c", script])
        return json.loads(completed.stdout.strip())


@pytest.fixture
def distribution_env() -> DistributionEnv:
    return DistributionEnv(consumer_root=CONSUMER_ROOT)


def declared_package_version(repo_root: Path) -> str:
    with (repo_root / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


@pytest.fixture
def package_version(repo_root: Path) -> str:
    return declared_package_version(repo_root)


@pytest.fixture
def built_wheel(repo_root: Path, tmp_path: Path, package_version: str) -> Path:
    env = DistributionEnv(consumer_root=CONSUMER_ROOT)
    return env.build_wheel(
        repo_root, tmp_path / "agent-brain-dist", version=package_version
    )
