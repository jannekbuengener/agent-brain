"""Read-only local repository inventory with explicit identity evidence."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from agent_brain.contracts import RepositoryProfile
from agent_brain.core.canonical import canonical_hash

INVENTORY_SCHEMA = "repository-inventory/v1"


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _canonical_remote(value: str) -> str:
    value = value.strip().rstrip("/").removesuffix(".git")
    if "@" in value and ":" in value and "://" not in value:
        host_and_path = value.split("@", 1)[1]
        host, path = host_and_path.split(":", 1)
        return f"{host.lower()}/{path.strip('/').lower()}"
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.netloc.lower()}/{parsed.path.strip('/').lower()}"
    return value.lower()


@dataclass(frozen=True, slots=True)
class RepositoryInventorySpec:
    """One explicitly configured local root and its portable repository profile."""

    key: str
    local_root: Path
    profile: RepositoryProfile
    required: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _required_text(self.key, "key"))
        if not isinstance(self.local_root, Path):
            raise TypeError("local_root must be a Path")
        if not isinstance(self.profile, RepositoryProfile):
            raise TypeError("profile must be a RepositoryProfile")
        if not isinstance(self.required, bool):
            raise TypeError("required must be a bool")


@dataclass(frozen=True, slots=True)
class RepositoryInventoryEntry:
    """Displayable local evidence without conflating it with configured identity."""

    key: str
    local_path: str
    local_status: Literal["OK", "MISSING", "LIMITED"]
    source_id: str
    repository: str
    configured_source_uri: str | None
    observed_origin_uri: str | None
    origin_matches_profile: bool | None
    limitations: tuple[str, ...]
    required: bool

    def __post_init__(self) -> None:
        for field_name in ("key", "local_path", "source_id", "repository"):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if self.local_status not in {"OK", "MISSING", "LIMITED"}:
            raise ValueError("local_status must be OK, MISSING, or LIMITED")
        if self.configured_source_uri is not None:
            object.__setattr__(
                self,
                "configured_source_uri",
                _required_text(self.configured_source_uri, "configured_source_uri"),
            )
        if self.observed_origin_uri is not None:
            object.__setattr__(
                self,
                "observed_origin_uri",
                _required_text(self.observed_origin_uri, "observed_origin_uri"),
            )
        if self.origin_matches_profile is not None and not isinstance(
            self.origin_matches_profile, bool
        ):
            raise TypeError("origin_matches_profile must be a bool or None")
        if not isinstance(self.limitations, (tuple, list)) or not all(
            isinstance(item, str) and item.strip() for item in self.limitations
        ):
            raise TypeError("limitations must contain non-blank strings")
        if not isinstance(self.required, bool):
            raise TypeError("required must be a bool")
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "local_path": self.local_path,
            "local_status": self.local_status,
            "source_id": self.source_id,
            "repository": self.repository,
            "configured_source_uri": self.configured_source_uri,
            "observed_origin_uri": self.observed_origin_uri,
            "origin_matches_profile": self.origin_matches_profile,
            "limitations": list(self.limitations),
            "required": self.required,
        }

    def identity_payload(self) -> dict[str, object]:
        """Return the host-independent subset used for the stable report hash."""
        return {
            "key": self.key,
            "local_status": self.local_status,
            "source_id": self.source_id,
            "repository": self.repository,
            "configured_source_uri": self.configured_source_uri,
            "observed_origin_uri": self.observed_origin_uri,
            "origin_matches_profile": self.origin_matches_profile,
            "limitations": list(self.limitations),
            "required": self.required,
        }


def build_inventory_fingerprint(entries: Sequence[RepositoryInventoryEntry]) -> str:
    """Hash only repository identity evidence, never machine-local display paths."""
    if not all(isinstance(entry, RepositoryInventoryEntry) for entry in entries):
        raise TypeError("entries must contain RepositoryInventoryEntry values")
    payloads = sorted((entry.identity_payload() for entry in entries), key=lambda item: str(item["key"]))
    return canonical_hash({"schema_version": INVENTORY_SCHEMA, "entries": payloads})


@dataclass(frozen=True, slots=True)
class RepositoryInventoryReport:
    """Deterministic inventory result for configured local repository roots."""

    schema_version: str
    entries: tuple[RepositoryInventoryEntry, ...]
    verdict: Literal["pass", "pass_with_limits", "fail"]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != INVENTORY_SCHEMA:
            raise ValueError(f"schema_version must be {INVENTORY_SCHEMA}")
        if not all(isinstance(entry, RepositoryInventoryEntry) for entry in self.entries):
            raise TypeError("entries must contain RepositoryInventoryEntry values")
        if self.verdict not in {"pass", "pass_with_limits", "fail"}:
            raise ValueError("verdict must be pass, pass_with_limits, or fail")
        object.__setattr__(self, "fingerprint", _required_text(self.fingerprint, "fingerprint"))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "entries": [entry.to_dict() for entry in sorted(self.entries, key=lambda entry: entry.key)],
            "verdict": self.verdict,
            "fingerprint": self.fingerprint,
        }


def read_git_origin(root: Path) -> str | None:
    """Read the local origin URL without contacting any remote."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _entry_from_spec(
    spec: RepositoryInventorySpec,
    origin_reader: Callable[[Path], str | None],
) -> RepositoryInventoryEntry:
    source = spec.profile.source
    local_path = str(spec.local_root.absolute())
    if not spec.local_root.is_dir():
        return RepositoryInventoryEntry(
            key=spec.key,
            local_path=local_path,
            local_status="MISSING",
            source_id=source.source_id,
            repository=source.repository,
            configured_source_uri=source.source_uri,
            observed_origin_uri=None,
            origin_matches_profile=None,
            limitations=("local root is missing",),
            required=spec.required,
        )
    if not (spec.local_root / ".git").exists():
        return RepositoryInventoryEntry(
            key=spec.key,
            local_path=local_path,
            local_status="LIMITED",
            source_id=source.source_id,
            repository=source.repository,
            configured_source_uri=source.source_uri,
            observed_origin_uri=None,
            origin_matches_profile=None,
            limitations=("local git metadata is unavailable",),
            required=spec.required,
        )
    try:
        observed_origin = origin_reader(spec.local_root)
    except FileNotFoundError:
        return RepositoryInventoryEntry(
            key=spec.key,
            local_path=local_path,
            local_status="LIMITED",
            source_id=source.source_id,
            repository=source.repository,
            configured_source_uri=source.source_uri,
            observed_origin_uri=None,
            origin_matches_profile=None,
            limitations=("local git unavailable",),
            required=spec.required,
        )
    except OSError:
        observed_origin = None
    if observed_origin is None:
        return RepositoryInventoryEntry(
            key=spec.key,
            local_path=local_path,
            local_status="LIMITED",
            source_id=source.source_id,
            repository=source.repository,
            configured_source_uri=source.source_uri,
            observed_origin_uri=None,
            origin_matches_profile=None,
            limitations=("origin remote is unavailable",),
            required=spec.required,
        )
    matches: bool | None = None
    limitations: tuple[str, ...] = ()
    status: Literal["OK", "LIMITED"] = "OK"
    if source.source_uri is not None:
        matches = _canonical_remote(source.source_uri) == _canonical_remote(observed_origin)
        if not matches:
            limitations = ("configured source differs from observed origin",)
            status = "LIMITED"
    return RepositoryInventoryEntry(
        key=spec.key,
        local_path=local_path,
        local_status=status,
        source_id=source.source_id,
        repository=source.repository,
        configured_source_uri=source.source_uri,
        observed_origin_uri=observed_origin,
        origin_matches_profile=matches,
        limitations=limitations,
        required=spec.required,
    )


def build_repository_inventory(
    specs: Sequence[RepositoryInventorySpec],
    *,
    origin_reader: Callable[[Path], str | None] = read_git_origin,
) -> RepositoryInventoryReport:
    """Build a local-only report without inferring ownership from the root path."""
    if not all(isinstance(spec, RepositoryInventorySpec) for spec in specs):
        raise TypeError("specs must contain RepositoryInventorySpec values")
    if len({spec.key for spec in specs}) != len(specs):
        raise ValueError("spec keys must be unique")
    entries = tuple(_entry_from_spec(spec, origin_reader) for spec in sorted(specs, key=lambda item: item.key))
    if any(entry.required and entry.local_status == "MISSING" for entry in entries):
        verdict: Literal["pass", "pass_with_limits", "fail"] = "fail"
    elif any(entry.local_status != "OK" for entry in entries):
        verdict = "pass_with_limits"
    else:
        verdict = "pass"
    return RepositoryInventoryReport(
        schema_version=INVENTORY_SCHEMA,
        entries=entries,
        verdict=verdict,
        fingerprint=build_inventory_fingerprint(entries),
    )
