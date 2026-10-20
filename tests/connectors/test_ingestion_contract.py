from __future__ import annotations

import pytest

from agent_brain.connectors.ingestion import (
    INGESTION_RESULT_SCHEMA,
    ForbiddenRule,
    IngestionFinding,
    IngestionPolicy,
    RepositoryIngestionResult,
    SensitivityRule,
    build_ingestion_fingerprint,
)
from agent_brain.contracts import (
    ArtifactRef,
    GraphEdge,
    IndexRecord,
    RepositoryProfile,
    RepositorySource,
)


def _source() -> RepositorySource:
    return RepositorySource(
        schema_version="repository-source/v1",
        source_id="source-widgets",
        repository="example/widgets",
        revision="abc123",
        source_uri="https://example.invalid/widgets.git",
    )


def _artifact() -> ArtifactRef:
    return ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id="artifact-widget",
        source_id="source-widgets",
        source_path="src/widget.py",
        source_hash="a" * 64,
        revision="abc123",
    )


def _records() -> tuple[IndexRecord, GraphEdge]:
    artifact = _artifact()
    record = IndexRecord(
        schema_version="index-record/v1",
        record_id="record-widget",
        record_type="code_symbol",
        source=artifact,
        content_hash="b" * 64,
        attributes={"name": "Widget"},
    )
    edge = GraphEdge(
        schema_version="graph-edge/v1",
        edge_id="edge-contains",
        from_id="artifact-widget",
        to_id="record-widget",
        edge_type="contains",
        source=artifact,
    )
    return record, edge


def test_policy_and_result_are_immutable_and_use_shared_contracts() -> None:
    source = _source()
    profile = RepositoryProfile(
        schema_version="repository-profile/v1",
        profile_id="profile-widgets",
        source=source,
    )
    record, edge = _records()
    policy = IngestionPolicy(
        sensitivity_rules=(SensitivityRule("private/**", "restricted", "caller policy"),),
        forbidden_rules=(ForbiddenRule("*.secret", "path", "caller policy"),),
        max_file_size_bytes=1024,
    )
    finding = IngestionFinding("private/value.txt", "forbidden", "caller policy")
    fingerprint = build_ingestion_fingerprint(
        source=source,
        profile_id=profile.profile_id,
        artifacts=(_artifact(),),
        records=(record,),
        edges=(edge,),
        findings=(finding,),
    )
    result = RepositoryIngestionResult(
        schema_version=INGESTION_RESULT_SCHEMA,
        source=source,
        profile_id=profile.profile_id,
        artifacts=(_artifact(),),
        records=(record,),
        edges=(edge,),
        findings=(finding,),
        fingerprint=fingerprint,
    )

    assert result.to_dict()["artifacts"][0]["schema_version"] == "artifact-ref/v1"
    assert result.to_dict()["records"][0]["schema_version"] == "index-record/v1"
    assert result.to_dict()["edges"][0]["schema_version"] == "graph-edge/v1"
    with pytest.raises((AttributeError, TypeError)):
        policy.max_file_size_bytes = 1  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        result.profile_id = "other"  # type: ignore[misc]


@pytest.mark.parametrize("size", [0, -1, True])
def test_policy_requires_positive_non_boolean_size(size: object) -> None:
    with pytest.raises((TypeError, ValueError), match="max_file_size_bytes"):
        IngestionPolicy(max_file_size_bytes=size)  # type: ignore[arg-type]


@pytest.mark.parametrize("target", ["url", "", "PATH"])
def test_forbidden_rule_rejects_unknown_targets(target: str) -> None:
    with pytest.raises(ValueError, match="target"):
        ForbiddenRule("pattern", target, "reason")  # type: ignore[arg-type]


def test_fingerprint_is_order_host_and_clock_independent() -> None:
    source = _source()
    record, edge = _records()
    first = build_ingestion_fingerprint(
        source=source,
        profile_id="profile-widgets",
        artifacts=(_artifact(),),
        records=(record,),
        edges=(edge,),
        findings=(IngestionFinding("docs/readme.md", "skipped", "excluded"),),
    )
    second = build_ingestion_fingerprint(
        source=source,
        profile_id="profile-widgets",
        artifacts=(_artifact(),),
        records=(record,),
        edges=(edge,),
        findings=(IngestionFinding("docs/readme.md", "skipped", "excluded"),),
    )

    assert first == second
    assert "D:\\" not in first
    assert "2026" not in first
