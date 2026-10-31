"""Canonical package version source of truth for Agent Brain."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

PACKAGE_NAME = "agent-brain"

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


@dataclass(frozen=True, slots=True)
class PackageVersion:
    """Parsed semantic version for the distributable package."""

    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    build: str | None = None

    @property
    def text(self) -> str:
        value = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            value = f"{value}-{self.prerelease}"
        if self.build:
            value = f"{value}+{self.build}"
        return value

    def __str__(self) -> str:
        return self.text


def parse_package_version(value: str) -> PackageVersion:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("package version must be a non-empty string")
    match = _SEMVER_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"invalid package version: {value!r}")
    return PackageVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease=match.group("prerelease"),
        build=match.group("build"),
    )


def version_git_tag(version: str | PackageVersion) -> str:
    """Return the canonical immutable git tag for a package version."""
    text = version.text if isinstance(version, PackageVersion) else parse_package_version(version).text
    return f"v{text}"


def get_package_version() -> str:
    """Return the installed package version (runtime source of truth)."""
    return metadata.version(PACKAGE_NAME)


def declared_version_from_pyproject(pyproject_path: Path) -> str:
    """Read the single declared version from pyproject.toml."""
    with pyproject_path.open("rb") as handle:
        project = tomllib.load(handle)["project"]
    version = project["version"]
    if not isinstance(version, str):
        raise TypeError("pyproject project.version must be a string")
    parse_package_version(version)
    return version
