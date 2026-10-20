from __future__ import annotations

from pathlib import Path

from agent_brain.connectors.inventory import (
    INVENTORY_SCHEMA,
    RepositoryInventorySpec,
    build_repository_inventory,
)
from agent_brain.contracts import RepositoryProfile, RepositorySource


def _profile() -> RepositoryProfile:
    return RepositoryProfile(
        schema_version="repository-profile/v1",
        profile_id="profile-widgets",
        source=RepositorySource(
            schema_version="repository-source/v1",
            source_id="source-widgets",
            repository="example/widgets",
            source_uri="https://example.invalid/widgets.git",
        ),
    )


def _repository(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / ".git").mkdir()
    return root


def test_inventory_handles_required_and_optional_missing_roots(tmp_path: Path) -> None:
    present = _repository(tmp_path / "present")
    report = build_repository_inventory(
        (
            RepositoryInventorySpec("optional", tmp_path / "missing-optional", _profile()),
            RepositoryInventorySpec("required", present, _profile(), required=True),
        ),
        origin_reader=lambda _root: "https://example.invalid/widgets.git",
    )

    assert report.schema_version == INVENTORY_SCHEMA
    assert [entry.key for entry in report.entries] == ["optional", "required"]
    assert report.entries[0].local_status == "MISSING"
    assert report.verdict == "pass_with_limits"

    failed = build_repository_inventory(
        (RepositoryInventorySpec("required", tmp_path / "missing-required", _profile(), True),)
    )
    assert failed.verdict == "fail"


def test_inventory_reports_limited_git_metadata_without_crashing(tmp_path: Path) -> None:
    no_git = tmp_path / "no-git"
    no_git.mkdir()
    with_origin = _repository(tmp_path / "origin-missing")
    unavailable = _repository(tmp_path / "git-unavailable")

    report = build_repository_inventory(
        (
            RepositoryInventorySpec("no-git", no_git, _profile()),
            RepositoryInventorySpec("origin-missing", with_origin, _profile()),
            RepositoryInventorySpec("git-unavailable", unavailable, _profile()),
        ),
        origin_reader=lambda root: (_ for _ in ()).throw(FileNotFoundError())
        if root == unavailable
        else None,
    )

    entries = {entry.key: entry for entry in report.entries}
    assert all(entry.local_status == "LIMITED" for entry in entries.values())
    assert entries["no-git"].observed_origin_uri is None
    assert any("git unavailable" in item for item in entries["git-unavailable"].limitations)
    assert report.verdict == "pass_with_limits"


def test_inventory_keeps_local_configured_and_observed_identity_separate(tmp_path: Path) -> None:
    local_root = _repository(tmp_path / "unrelated-local-folder")
    report = build_repository_inventory(
        (RepositoryInventorySpec("primary", local_root, _profile(), required=True),),
        origin_reader=lambda _root: "https://example.invalid/other.git",
    )

    entry = report.entries[0]
    assert entry.local_path.endswith("unrelated-local-folder")
    assert entry.repository == "example/widgets"
    assert entry.configured_source_uri == "https://example.invalid/widgets.git"
    assert entry.observed_origin_uri == "https://example.invalid/other.git"
    assert entry.origin_matches_profile is False
    assert entry.local_status == "LIMITED"
    assert any("differs" in item for item in entry.limitations)


def test_inventory_fingerprint_is_relocation_and_order_independent(tmp_path: Path) -> None:
    first_root = _repository(tmp_path / "host-a" / "checkout")
    second_root = _repository(tmp_path / "host-b" / "checkout")
    first = build_repository_inventory(
        (RepositoryInventorySpec("widgets", first_root, _profile(), required=True),),
        origin_reader=lambda _root: "https://example.invalid/widgets.git",
    )
    second = build_repository_inventory(
        (RepositoryInventorySpec("widgets", second_root, _profile(), required=True),),
        origin_reader=lambda _root: "https://example.invalid/widgets.git",
    )

    assert first.fingerprint == second.fingerprint
    assert first.entries[0].local_path != second.entries[0].local_path
