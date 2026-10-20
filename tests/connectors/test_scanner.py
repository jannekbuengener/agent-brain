from __future__ import annotations

from pathlib import Path

from agent_brain.connectors.ingestion import ForbiddenRule, IngestionPolicy, SensitivityRule
from agent_brain.connectors.scanner import classify_file_type, scan_repository
from agent_brain.contracts import RepositoryProfile, RepositorySource


def _profile(
    *, include_paths: tuple[str, ...] = ("src/", "docs/", "config/"),
    exclude_paths: tuple[str, ...] = ("excluded/",),
    allowed_file_types: tuple[str, ...] = ("python", "markdown", "toml", "json", "text"),
) -> RepositoryProfile:
    return RepositoryProfile(
        schema_version="repository-profile/v1",
        profile_id="profile-widgets",
        source=RepositorySource(
            schema_version="repository-source/v1",
            source_id="source-widgets",
            repository="example/widgets",
            revision="abc123",
        ),
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        allowed_file_types=allowed_file_types,
    )


def _write(root: Path, relative_path: str, content: bytes) -> Path:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def test_file_type_classification_is_generic() -> None:
    assert classify_file_type("src/widget.py") == "python"
    assert classify_file_type("docs/readme.md") == "markdown"
    assert classify_file_type("config/settings.toml") == "toml"
    assert classify_file_type("config/settings.json") == "json"
    assert classify_file_type("config/settings.yaml") == "yaml"
    assert classify_file_type("notes.txt") == "text"
    assert classify_file_type("archive.bin") is None


def test_scanner_applies_profile_rules_and_normalizes_line_endings(tmp_path: Path) -> None:
    _write(tmp_path, "src/widget.py", b"def widget():\r\n    return 1\r\n")
    _write(tmp_path, "docs/readme.md", b"# Widget\n")
    _write(tmp_path, "excluded/ignore.py", b"raise RuntimeError\n")
    result = scan_repository(tmp_path, _profile(), IngestionPolicy())

    assert [source.ref.source_path for source in result.sources] == [
        "docs/readme.md",
        "src/widget.py",
    ]
    assert result.sources[1].text == "def widget():\n    return 1\n"
    assert result.sources[1].ref.artifact_id.startswith("artifact-")
    assert result.findings == ()


def test_scanner_fails_closed_for_unsafe_and_unreadable_content(tmp_path: Path) -> None:
    _write(tmp_path, "src/large.py", b"x" * 32)
    _write(tmp_path, "src/binary.py", b"\x00binary")
    _write(tmp_path, "src/invalid.py", b"\xff")
    _write(tmp_path, "src/content.py", b"forbidden-content")
    _write(tmp_path, "src/secret.py", b"TOKEN=not-for-output")
    _write(tmp_path, "private/value.txt", b"TOKEN=not-for-output")
    policy = IngestionPolicy(
        forbidden_rules=(
            ForbiddenRule("private/**", "path", "private material"),
            ForbiddenRule("forbidden-content", "content", "blocked material"),
        ),
        max_file_size_bytes=16,
    )
    result = scan_repository(tmp_path, _profile(include_paths=("src/", "private/")), policy)

    assert result.sources == ()
    rendered = [finding.to_dict() for finding in result.findings]
    assert {finding["status"] for finding in rendered} == {"forbidden", "limited"}
    assert "not-for-output" not in str(rendered)


def test_scanner_rejects_profile_path_escapes_and_preserves_sensitivity(tmp_path: Path) -> None:
    _write(tmp_path, "private/note.txt", b"safe content")
    policy = IngestionPolicy(
        sensitivity_rules=(SensitivityRule("private/**", "restricted", "caller supplied"),),
    )
    result = scan_repository(
        tmp_path,
        _profile(include_paths=("../outside", "private/"), exclude_paths=("/absolute",)),
        policy,
    )

    assert [source.sensitivity for source in result.sources] == ["restricted"]
    assert all(finding.status == "forbidden" for finding in result.findings)


def test_scanner_rejects_symlink_escape_when_supported(tmp_path: Path) -> None:
    external = tmp_path.parent / "outside.txt"
    external.write_text("outside", encoding="utf-8")
    link = tmp_path / "src" / "outside.txt"
    link.parent.mkdir()
    try:
        link.symlink_to(external)
    except OSError:
        return

    result = scan_repository(tmp_path, _profile(include_paths=("src/",)), IngestionPolicy())

    assert result.sources == ()
    assert result.findings[0].status == "forbidden"
