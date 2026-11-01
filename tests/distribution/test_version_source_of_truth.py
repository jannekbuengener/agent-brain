from __future__ import annotations

import tomllib

import agent_brain
from agent_brain.distribution import (
    PACKAGE_NAME,
    declared_version_from_pyproject,
    get_package_version,
    parse_package_version,
    version_git_tag,
)
from agent_brain.knowledge.builder import DEFAULT_TOOL_VERSION


def test_pyproject_is_single_declared_version_source(repo_root) -> None:
    declared = declared_version_from_pyproject(repo_root / "pyproject.toml")
    parsed = parse_package_version(declared)

    assert declared == "0.3.0"
    assert parsed.text == "0.3.0"
    assert get_package_version() == declared
    assert agent_brain.__version__ == declared


def test_runtime_version_matches_importlib_metadata() -> None:
    assert get_package_version() == agent_brain.__version__
    assert PACKAGE_NAME == "agent-brain"


def test_git_tag_convention_matches_package_version() -> None:
    assert version_git_tag("0.3.0") == "v0.3.0"
    assert version_git_tag(parse_package_version("0.3.0")) == "v0.3.0"


def test_knowledge_tool_version_tracks_package_semver() -> None:
    assert DEFAULT_TOOL_VERSION == f"agent-brain/{get_package_version()}"


def test_pyproject_python_constraint_and_empty_runtime_deps(repo_root) -> None:
    with (repo_root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    assert project["requires-python"] == ">=3.12"
    assert project["dependencies"] == []
    assert project["name"] == PACKAGE_NAME
