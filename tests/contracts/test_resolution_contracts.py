from __future__ import annotations

import pytest

from agent_brain.contracts.resolution import ResolutionMeta, ResolutionState


def test_resolution_meta_preserves_supersession_links_without_resolving_them() -> None:
    meta = ResolutionMeta(
        schema_version="resolution-meta/v1",
        supersedes_ref=" claim:old ",
        superseded_by_ref="claim:new",
        supersession_reason=" correction ",
    )

    assert meta.to_dict() == {
        "schema_version": "resolution-meta/v1",
        "supersedes_ref": "claim:old",
        "superseded_by_ref": "claim:new",
        "supersession_reason": "correction",
    }
    assert ResolutionMeta.from_dict(meta.to_dict()) == meta


def test_source_trust_and_confidence_are_independent_values() -> None:
    meta = ResolutionMeta(
        schema_version="resolution-meta/v1",
        source_trust=0.95,
        confidence=0.25,
    )

    assert meta.source_trust == 0.95
    assert meta.confidence == 0.25
    assert meta.to_dict()["source_trust"] == 0.95
    assert meta.to_dict()["confidence"] == 0.25


@pytest.mark.parametrize("field", ["source_trust", "confidence"])
@pytest.mark.parametrize("value", [-0.01, 1.01, True, False, "0.5"])
def test_resolution_meta_rejects_invalid_scores(field: str, value) -> None:
    kwargs = {field: value}
    with pytest.raises((TypeError, ValueError), match=field):
        ResolutionMeta(schema_version="resolution-meta/v1", **kwargs)


def test_resolution_state_has_exact_read_side_values() -> None:
    assert [state.value for state in ResolutionState] == [
        "CURRENT",
        "STALE",
        "SUPERSEDED",
        "UNKNOWN",
    ]


def test_resolution_state_is_not_stored_in_resolution_meta() -> None:
    meta = ResolutionMeta.from_dict(
        {
            "schema_version": "resolution-meta/v1",
            "source_trust": 0.8,
            "resolution_state": "STALE",
        }
    )

    assert not hasattr(meta, "resolution_state")
    assert "resolution_state" not in meta.to_dict()


def test_resolution_meta_rejects_incompatible_major() -> None:
    with pytest.raises(ValueError, match="major"):
        ResolutionMeta(schema_version="resolution-meta/v2")
