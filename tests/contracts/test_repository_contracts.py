from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_brain.contracts.repository import ArtifactRef, RepositoryProfile, RepositorySource

FIXTURE = Path("tests/fixtures/contracts/repository_profile.neutral.v1.json")


def test_repository_profile_fixture_round_trip_is_deterministic() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    profile = RepositoryProfile.from_dict(payload)

    assert profile.profile_id == "profile-example"
    assert profile.source.repository == "example/widgets"
    assert profile.source.revision == "abc123"
    assert profile.include_paths == ("src/", "docs/")
    assert profile.to_dict() == payload


def test_repository_profile_ignores_unknown_additive_v1_fields() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["future_optional_field"] = {"enabled": True}

    profile = RepositoryProfile.from_dict(payload)

    assert profile.profile_id == "profile-example"
    assert "future_optional_field" not in profile.to_dict()


@pytest.mark.parametrize("field", ["include_paths", "exclude_paths", "allowed_file_types"])
def test_repository_profile_rejects_string_where_sequence_is_required(field: str) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload[field] = "src/"

    with pytest.raises(TypeError, match=field):
        RepositoryProfile.from_dict(payload)


def test_repository_source_round_trip() -> None:
    source = RepositorySource(
        schema_version="repository-source/v1",
        source_id="source-example",
        repository="example/widgets",
        revision="abc123",
        source_uri="https://example.invalid/widgets.git",
    )

    assert RepositorySource.from_dict(source.to_dict()) == source


def test_artifact_ref_round_trip() -> None:
    artifact = ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id="artifact-example",
        source_id="source-example",
        source_path="src/widget.py",
        source_hash="a" * 64,
        revision="abc123",
    )

    assert ArtifactRef.from_dict(artifact.to_dict()) == artifact


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (
            lambda: RepositorySource(
                schema_version="repository-source/v1",
                source_id=" ",
                repository="example/widgets",
            ),
            "source_id",
        ),
        (
            lambda: RepositorySource(
                schema_version="repository-source/v1",
                source_id="source-example",
                repository=" ",
            ),
            "repository",
        ),
        (
            lambda: RepositoryProfile(
                schema_version="repository-profile/v1",
                profile_id=" ",
                source=RepositorySource(
                    schema_version="repository-source/v1",
                    source_id="source-example",
                    repository="example/widgets",
                ),
            ),
            "profile_id",
        ),
        (
            lambda: ArtifactRef(
                schema_version="artifact-ref/v1",
                artifact_id=" ",
                source_id="source-example",
                source_path="src/widget.py",
                source_hash="a" * 64,
            ),
            "artifact_id",
        ),
        (
            lambda: ArtifactRef(
                schema_version="artifact-ref/v1",
                artifact_id="artifact-example",
                source_id="source-example",
                source_path=" ",
                source_hash="a" * 64,
            ),
            "source_path",
        ),
        (
            lambda: ArtifactRef(
                schema_version="artifact-ref/v1",
                artifact_id="artifact-example",
                source_id="source-example",
                source_path="src/widget.py",
                source_hash=" ",
            ),
            "source_hash",
        ),
    ],
)
def test_repository_contracts_reject_blank_required_fields(factory, field: str) -> None:
    with pytest.raises(ValueError, match=field):
        factory()


def test_repository_contracts_reject_incompatible_major() -> None:
    with pytest.raises(ValueError, match="major"):
        RepositorySource(
            schema_version="repository-source/v2",
            source_id="source-example",
            repository="example/widgets",
        )
