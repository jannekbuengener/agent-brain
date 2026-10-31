"""Protocol test fixtures (wheel build helpers reused from distribution)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.distribution.conftest import (
    CONSUMER_ROOT,
    DistributionEnv,
    declared_package_version,
)


@pytest.fixture
def distribution_env() -> DistributionEnv:
    return DistributionEnv(consumer_root=CONSUMER_ROOT)


@pytest.fixture
def package_version(repo_root: Path) -> str:
    return declared_package_version(repo_root)


@pytest.fixture
def built_wheel(repo_root: Path, tmp_path: Path, package_version: str) -> Path:
    env = DistributionEnv(consumer_root=CONSUMER_ROOT)
    return env.build_wheel(
        repo_root, tmp_path / "agent-brain-dist", version=package_version
    )
