"""Protocol test fixtures (wheel build helpers reused from distribution)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.distribution.conftest import CONSUMER_ROOT, DistributionEnv


@pytest.fixture
def distribution_env() -> DistributionEnv:
    return DistributionEnv(consumer_root=CONSUMER_ROOT)


@pytest.fixture
def built_wheel(repo_root: Path, tmp_path: Path) -> Path:
    env = DistributionEnv(consumer_root=CONSUMER_ROOT)
    return env.build_wheel(repo_root, tmp_path / "agent-brain-dist", version="0.1.0")
