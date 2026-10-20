from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root for tests that validate repository contracts."""
    return Path(__file__).resolve().parents[1]
