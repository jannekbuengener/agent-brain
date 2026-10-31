"""Immutable pinning contract for external Agent Brain consumers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from agent_brain.distribution.version import (
    PACKAGE_NAME,
    get_package_version,
    parse_package_version,
    version_git_tag,
)

# Canonical distribution model: one primary mechanism.
# Consumers pin an exact package version. The matching immutable git tag is
# ``v{version}``. Built wheels/sdists carry the same version metadata.
DISTRIBUTION_MODEL = "exact-package-version+matching-git-tag"

FORBIDDEN_PIN_REFS: frozenset[str] = frozenset(
    {
        "main",
        "master",
        "HEAD",
        "latest",
        "origin/main",
        "origin/master",
    }
)

_LOCAL_PATH_RE = re.compile(r"^(?:\./|\.\./|/|[A-Za-z]:\\).+")
_EXACT_VERSION_RE = re.compile(rf"^{re.escape(PACKAGE_NAME)}\s*==\s*(?P<version>[^\s;]+)\s*$")
_GIT_REQ_RE = re.compile(
    rf"^(?:{re.escape(PACKAGE_NAME)}\s*@\s*)?"
    r"git\+https://github\.com/[^/\s]+/agent-brain(?:\.git)?@(?P<ref>\S+)\s*$"
)


class PinKind(str, Enum):
    EXACT_VERSION = "exact_version"
    GIT_TAG = "git_tag"
    GIT_COMMIT = "git_commit"


@dataclass(frozen=True, slots=True)
class PinSpec:
    """Immutable consumer pin for Agent Brain."""

    kind: PinKind
    version: str | None
    reference: str

    def __post_init__(self) -> None:
        reject_moving_ref(self.reference)
        if self.version is not None:
            parse_package_version(self.version)


def reject_moving_ref(reference: str) -> None:
    """Reject branch/`latest`/HEAD pins that are not reproducible."""
    normalized = reference.strip()
    if not normalized:
        raise ValueError("pin reference must be non-empty")
    lowered = {item.lower() for item in FORBIDDEN_PIN_REFS}
    if normalized in FORBIDDEN_PIN_REFS or normalized.lower() in lowered:
        raise ValueError(f"moving pin reference is forbidden: {reference!r}")
    if normalized.startswith("origin/") and normalized.split("/", 1)[-1] in {"main", "master"}:
        raise ValueError(f"moving pin reference is forbidden: {reference!r}")


def format_requirement(pin: PinSpec, *, repository_url: str | None = None) -> str:
    """Render a PEP 508 requirement for the pin."""
    if pin.kind is PinKind.EXACT_VERSION:
        if pin.version is None:
            raise ValueError("exact version pin requires version")
        return f"{PACKAGE_NAME}=={pin.version}"
    if pin.kind is PinKind.GIT_TAG:
        if pin.version is None:
            raise ValueError("git tag pin requires version")
        url = repository_url or "https://github.com/jannekbuengener/agent-brain.git"
        return f"{PACKAGE_NAME} @ git+{url}@{version_git_tag(pin.version)}"
    if pin.kind is PinKind.GIT_COMMIT:
        url = repository_url or "https://github.com/jannekbuengener/agent-brain.git"
        return f"{PACKAGE_NAME} @ git+{url}@{pin.reference}"
    raise ValueError(f"unsupported pin kind: {pin.kind}")


def parse_pin_spec(requirement: str) -> PinSpec:
    """Parse a consumer pin requirement into a PinSpec (fail closed)."""
    text = requirement.strip()
    if not text:
        raise ValueError("requirement must be non-empty")

    if _LOCAL_PATH_RE.fullmatch(text) is not None:
        raise ValueError(
            "unversioned local paths are not a canonical consumer pin; "
            "use an exact version, git tag, or immutable commit"
        )

    exact = _EXACT_VERSION_RE.fullmatch(text)
    if exact is not None:
        version = exact.group("version")
        parse_package_version(version)
        return PinSpec(kind=PinKind.EXACT_VERSION, version=version, reference=version)

    git = _GIT_REQ_RE.fullmatch(text)
    if git is not None:
        ref = git.group("ref")
        reject_moving_ref(ref)
        if ref.startswith("v") and _looks_like_version(ref[1:]):
            version = ref[1:]
            parse_package_version(version)
            return PinSpec(kind=PinKind.GIT_TAG, version=version, reference=ref)
        if re.fullmatch(r"[0-9a-fA-F]{7,40}", ref):
            return PinSpec(kind=PinKind.GIT_COMMIT, version=None, reference=ref.lower())
        raise ValueError(f"git pin must use immutable tag v{{version}} or commit SHA: {ref!r}")

    raise ValueError(f"unsupported pin requirement: {requirement!r}")


def verify_installed_version(expected_version: str) -> str:
    """Verify the installed distribution matches the expected exact version."""
    parse_package_version(expected_version)
    installed = get_package_version()
    if installed != expected_version:
        raise ValueError(
            f"installed {PACKAGE_NAME} version {installed!r} does not match pin {expected_version!r}"
        )
    return installed


def _looks_like_version(value: str) -> bool:
    try:
        parse_package_version(value)
    except ValueError:
        return False
    return True
