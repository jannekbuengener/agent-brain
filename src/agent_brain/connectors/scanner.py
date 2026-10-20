"""Safe, read-only discovery of explicitly profiled local repository files."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from agent_brain.connectors.ingestion import IngestionFinding, IngestionPolicy
from agent_brain.contracts import ArtifactRef, RepositoryProfile
from agent_brain.core.canonical import canonical_hash, sha256_hex

_FILE_TYPES = {
    ".py": "python",
    ".md": "markdown",
    ".mdx": "markdown",
    ".toml": "toml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".txt": "text",
}
_SECRET_LIKE_RE = re.compile(
    r"(?i)(?:token|secret|password|passwd|credential|api[_-]?key|auth[_-]?token|"
    r"private[_-]?key)\s*[:=]\s*\S+|gh[pousr]_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)


@dataclass(frozen=True, slots=True)
class ScannedSource:
    """In-memory text permitted to enter the static extraction stage."""

    ref: ArtifactRef
    file_type: str
    sensitivity: str | None
    size_bytes: int
    text: str


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Sorted sources and safe findings from one local-only scan."""

    sources: tuple[ScannedSource, ...]
    findings: tuple[IngestionFinding, ...]


def classify_file_type(path: str) -> str | None:
    """Return a small, product-neutral type vocabulary based on a suffix."""
    return _FILE_TYPES.get(PurePosixPath(path.replace("\\", "/")).suffix.lower())


def _is_unsafe_rule_path(value: str) -> bool:
    if not value.strip():
        return True
    posix = PurePosixPath(value.replace("\\", "/"))
    windows = PureWindowsPath(value)
    return posix.is_absolute() or windows.is_absolute() or ".." in posix.parts or ".." in windows.parts


def _matches_path(rel_path: str, pattern: str) -> bool:
    normalized = pattern.replace("\\", "/").rstrip("/")
    if not normalized:
        return False
    return (
        rel_path == normalized
        or rel_path.startswith(f"{normalized}/")
        or fnmatch.fnmatchcase(rel_path, normalized)
        or fnmatch.fnmatchcase(rel_path, f"{normalized}/**")
    )


def _safe_rule_findings(profile: RepositoryProfile) -> tuple[IngestionFinding, ...]:
    findings: list[IngestionFinding] = []
    for value in (*profile.include_paths, *profile.exclude_paths):
        if _is_unsafe_rule_path(value):
            findings.append(
                IngestionFinding("<profile>", "forbidden", "unsafe profile path rule")
            )
    return tuple(findings)


def _is_included(rel_path: str, profile: RepositoryProfile) -> bool:
    safe_includes = tuple(path for path in profile.include_paths if not _is_unsafe_rule_path(path))
    return not safe_includes or any(_matches_path(rel_path, path) for path in safe_includes)


def _is_excluded(rel_path: str, profile: RepositoryProfile) -> bool:
    return any(
        _matches_path(rel_path, path)
        for path in profile.exclude_paths
        if not _is_unsafe_rule_path(path)
    )


def _sensitivity_for(rel_path: str, policy: IngestionPolicy) -> str | None:
    for rule in policy.sensitivity_rules:
        if _matches_path(rel_path, rule.path_pattern):
            return rule.classification
    return None


def _forbidden_path_rule(rel_path: str, policy: IngestionPolicy) -> str | None:
    for rule in policy.forbidden_rules:
        if rule.target == "path" and _matches_path(rel_path, rule.pattern):
            return rule.reason
    return None


def _forbidden_content_rule(text: str, policy: IngestionPolicy) -> str | None:
    for rule in policy.forbidden_rules:
        if rule.target == "content" and rule.pattern in text:
            return rule.reason
    return None


def _artifact_ref(profile: RepositoryProfile, rel_path: str, text: str) -> ArtifactRef:
    source_hash = sha256_hex(text.encode("utf-8"))
    artifact_id = f"artifact-{canonical_hash({
        'source_id': profile.source.source_id,
        'source_path': rel_path,
        'source_hash': source_hash,
    })}"
    return ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id=artifact_id,
        source_id=profile.source.source_id,
        source_path=rel_path,
        source_hash=source_hash,
        revision=profile.source.revision,
    )


def scan_repository(root: Path, profile: RepositoryProfile, policy: IngestionPolicy) -> ScanResult:
    """Read eligible text files under ``root`` without leaving its resolved boundary."""
    if not isinstance(root, Path):
        raise TypeError("root must be a Path")
    if not isinstance(profile, RepositoryProfile):
        raise TypeError("profile must be a RepositoryProfile")
    if not isinstance(policy, IngestionPolicy):
        raise TypeError("policy must be an IngestionPolicy")

    findings = list(_safe_rule_findings(profile))
    if not root.is_dir():
        findings.append(IngestionFinding("<repository>", "limited", "repository root is unavailable"))
        return ScanResult((), tuple(findings))

    resolved_root = root.resolve()
    sources: list[ScannedSource] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if path.is_dir():
            continue
        try:
            rel_path = path.relative_to(root).as_posix()
            resolved_path = path.resolve()
        except (OSError, ValueError):
            findings.append(IngestionFinding("<unresolved>", "forbidden", "path cannot be resolved"))
            continue
        if not resolved_path.is_relative_to(resolved_root):
            findings.append(IngestionFinding(rel_path, "forbidden", "path escapes repository root"))
            continue
        if not _is_included(rel_path, profile) or _is_excluded(rel_path, profile):
            continue
        file_type = classify_file_type(rel_path)
        if file_type is None or (
            profile.allowed_file_types and file_type not in profile.allowed_file_types
        ):
            continue
        sensitivity = _sensitivity_for(rel_path, policy)
        forbidden_reason = _forbidden_path_rule(rel_path, policy)
        if forbidden_reason is not None:
            findings.append(IngestionFinding(rel_path, "forbidden", forbidden_reason, sensitivity))
            continue
        try:
            size_bytes = path.stat().st_size
        except OSError:
            findings.append(IngestionFinding(rel_path, "limited", "file size is unavailable", sensitivity))
            continue
        if size_bytes > policy.max_file_size_bytes:
            findings.append(IngestionFinding(rel_path, "limited", "file exceeds size limit", sensitivity))
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            findings.append(IngestionFinding(rel_path, "limited", "file cannot be read", sensitivity))
            continue
        if b"\x00" in raw:
            findings.append(IngestionFinding(rel_path, "limited", "binary file is excluded", sensitivity))
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(IngestionFinding(rel_path, "limited", "file is not valid UTF-8", sensitivity))
            continue
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        forbidden_reason = _forbidden_content_rule(text, policy)
        if forbidden_reason is not None:
            findings.append(IngestionFinding(rel_path, "forbidden", forbidden_reason, sensitivity))
            continue
        if file_type not in {"toml", "json"} and _SECRET_LIKE_RE.search(text):
            findings.append(IngestionFinding(rel_path, "forbidden", "sensitive content is excluded", sensitivity))
            continue
        sources.append(
            ScannedSource(
                ref=_artifact_ref(profile, rel_path, text),
                file_type=file_type,
                sensitivity=sensitivity,
                size_bytes=size_bytes,
                text=text,
            )
        )
    return ScanResult(
        sources=tuple(sorted(sources, key=lambda source: source.ref.source_path)),
        findings=tuple(
            sorted(
                findings,
                key=lambda finding: (
                    finding.source_path,
                    finding.status,
                    finding.reason,
                    finding.sensitivity or "",
                ),
            )
        ),
    )
