from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_brain.context.package import (
    CONTEXT_PACKAGE_SCHEMA,
    ContextArtifact,
    ContextPackageError,
    ContextPackageRequest,
    build_context_package,
)
from agent_brain.contracts.evidence import EvidenceRef
from agent_brain.contracts.repository import ArtifactRef
from agent_brain.core.source_priority import SourcePriority

FIXTURE = Path("tests/fixtures/context/context_package.neutral.v2.json")


def _fixture() -> tuple[ArtifactRef, EvidenceRef]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return ArtifactRef.from_dict(payload["artifact"]), EvidenceRef.from_dict(payload["evidence"])


def _request(**overrides):
    artifact_ref, evidence_ref = _fixture()
    defaults = {
        "target_scope": "issue:example-42",
        "artifacts": (
            ContextArtifact(
                ref=artifact_ref,
                artifact_type="source",
                summary="Widget source",
                payload={"metadata": {"owner": "example-team"}},
            ),
        ),
        "source_priority": SourcePriority(("repository_live", "verified_evidence")),
        "evidence_refs": (evidence_ref,),
        "generated_at_or_as_of": "2026-10-20T20:00:00",
    }
    defaults.update(overrides)
    return ContextPackageRequest(**defaults)


def test_context_package_has_required_schema_and_shared_refs() -> None:
    package = build_context_package(_request())
    payload = package.to_dict()

    assert payload["schema_version"] == CONTEXT_PACKAGE_SCHEMA == "context-package/v2"
    assert payload["package_id"].startswith("pkg_")
    assert payload["target_scope"] == "issue:example-42"
    assert payload["source_priority"] == ["repository_live", "verified_evidence"]
    assert payload["artifacts"][0]["ref"]["schema_version"] == "artifact-ref/v1"
    assert payload["evidence_refs"][0]["schema_version"] == "evidence-ref/v1"


def test_package_id_is_deterministic_and_excludes_wall_clock() -> None:
    first = build_context_package(_request(generated_at_or_as_of="2026-10-20T20:00:00"))
    second = build_context_package(_request(generated_at_or_as_of="2026-10-21T08:15:00"))

    assert first.package_id == second.package_id
    assert first.content_hash == second.content_hash


def test_artifact_order_does_not_change_package_id() -> None:
    artifact_ref, _ = _fixture()
    second_ref = ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id="artifact-doc",
        source_id="source-example",
        source_path="docs/widget.md",
        source_hash="c" * 64,
        revision="abc123",
    )
    a = ContextArtifact(ref=artifact_ref, artifact_type="source", summary="Source")
    b = ContextArtifact(ref=second_ref, artifact_type="doc", summary="Docs")

    forward = build_context_package(_request(artifacts=(a, b)))
    reverse = build_context_package(_request(artifacts=(b, a)))

    assert forward.package_id == reverse.package_id
    assert [item.ref.artifact_id for item in forward.artifacts] == ["artifact-doc", "artifact-widget"]


def test_missing_optional_context_adds_limitations_without_fake_resolution() -> None:
    package = build_context_package(_request(ranked_context=None, evidence_refs=(), decision_refs=()))

    assert "ranked_context_not_provided" in package.limitations
    assert "evidence_refs_not_provided" in package.limitations
    assert "decision_refs_not_provided" in package.limitations


def test_sensitive_values_are_redacted_and_never_leak_to_summary() -> None:
    artifact_ref, _ = _fixture()
    secret = "sk-super-secret-value"
    package = build_context_package(
        _request(
            artifacts=(
                ContextArtifact(
                    ref=artifact_ref,
                    artifact_type="source",
                    payload={
                        "api_key": secret,
                        "nested": {"token": "Bearer abc.def.ghi"},
                        "source_url": "https://example.invalid/path?token=hidden-value",
                    },
                ),
            )
        )
    )
    serialized = json.dumps(package.to_dict(), sort_keys=True)

    assert secret not in serialized
    assert "hidden-value" not in serialized
    assert package.artifacts[0].payload["api_key"] == "[REDACTED]"
    assert package.redaction_summary
    assert all(secret not in entry.path for entry in package.redaction_summary)


def test_secret_only_differences_do_not_change_package_id() -> None:
    artifact_ref, _ = _fixture()

    def with_secret(secret: str):
        return _request(
            artifacts=(
                ContextArtifact(
                    ref=artifact_ref,
                    artifact_type="source",
                    payload={"api_key": secret},
                ),
            )
        )

    first = build_context_package(with_secret("sk-one-secret"))
    second = build_context_package(with_secret("sk-two-secret"))

    assert first.package_id == second.package_id


def test_required_read_secret_only_differences_do_not_change_package_id() -> None:
    first = build_context_package(
        _request(required_reads=({"path": "AGENTS.md", "api_key": "sk-one-secret"},))
    )
    second = build_context_package(
        _request(required_reads=({"path": "AGENTS.md", "api_key": "sk-two-secret"},))
    )

    assert first.package_id == second.package_id
    assert first.required_reads[0]["api_key"] == "[REDACTED]"


def test_blank_scope_and_empty_artifacts_fail_closed() -> None:
    with pytest.raises(ContextPackageError, match="target_scope"):
        build_context_package(_request(target_scope=" "))
    with pytest.raises(ContextPackageError, match="artifacts"):
        build_context_package(_request(artifacts=()))


def test_context_artifact_requires_shared_artifact_ref() -> None:
    with pytest.raises(TypeError, match="ArtifactRef"):
        ContextArtifact(ref={"artifact_id": "fake"}, artifact_type="source")  # type: ignore[arg-type]
