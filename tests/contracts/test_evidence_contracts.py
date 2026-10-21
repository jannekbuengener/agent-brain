from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_brain.contracts.evidence import ClaimRef, EvidenceRef

FIXTURE = Path("tests/fixtures/contracts/evidence_claim.neutral.v1.json")


def _load_fixture() -> tuple[EvidenceRef, ClaimRef]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return EvidenceRef.from_dict(payload["evidence"]), ClaimRef.from_dict(payload["claim"])


def test_evidence_and_claim_fixture_round_trip() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    evidence, claim = _load_fixture()

    assert evidence.to_dict() == payload["evidence"]
    assert claim.to_dict() == payload["claim"]


def test_empty_optional_relations_round_trip_as_empty_lists() -> None:
    evidence = EvidenceRef(
        schema_version="evidence-ref/v1",
        evidence_id="evidence-empty",
        evidence_type="observation",
    )
    claim = ClaimRef(
        schema_version="claim-ref/v1",
        claim_id="claim-empty",
        claim_type="assertion",
    )

    assert evidence.to_dict()["source_refs"] == []
    assert evidence.to_dict()["artifact_refs"] == []
    assert evidence.to_dict()["claim_refs"] == []
    assert evidence.to_dict()["decision_refs"] == []
    assert claim.to_dict()["evidence_refs"] == []
    assert claim.to_dict()["artifact_refs"] == []
    assert claim.to_dict()["decision_refs"] == []
    assert claim.to_dict()["source_refs"] == []


def test_evidence_ref_ignores_unrelated_authority_metadata() -> None:
    evidence, _ = _load_fixture()
    payload = evidence.to_dict()
    payload.update(
        {
            "trust_classification": "high",
            "brain_source": "external-store",
            "db_metadata": {"record_count": 3},
        }
    )

    restored = EvidenceRef.from_dict(payload)

    assert restored == evidence
    assert not hasattr(restored, "trust_classification")
    assert not hasattr(restored, "brain_source")
    assert "db_metadata" not in restored.to_dict()


def test_claim_ref_ignores_unrelated_authority_metadata() -> None:
    _, claim = _load_fixture()
    payload = claim.to_dict()
    payload.update(
        {
            "trust_classification": "low",
            "resolver_status": "supported",
            "freshness_score": 0.9,
        }
    )

    restored = ClaimRef.from_dict(payload)

    assert restored == claim
    assert not hasattr(restored, "trust_classification")
    assert not hasattr(restored, "resolver_status")
    assert "freshness_score" not in restored.to_dict()


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (
            lambda: EvidenceRef(
                schema_version="evidence-ref/v1",
                evidence_id=" ",
                evidence_type="observation",
            ),
            "evidence_id",
        ),
        (
            lambda: EvidenceRef(
                schema_version="evidence-ref/v1",
                evidence_id="evidence-example",
                evidence_type=" ",
            ),
            "evidence_type",
        ),
        (
            lambda: ClaimRef(
                schema_version="claim-ref/v1",
                claim_id=" ",
                claim_type="assertion",
            ),
            "claim_id",
        ),
        (
            lambda: ClaimRef(
                schema_version="claim-ref/v1",
                claim_id="claim-example",
                claim_type=" ",
            ),
            "claim_type",
        ),
    ],
)
def test_evidence_claim_contracts_reject_blank_required_fields(factory, field: str) -> None:
    with pytest.raises(ValueError, match=field):
        factory()


def test_relation_entries_must_not_be_blank() -> None:
    with pytest.raises(ValueError, match="artifact_refs"):
        EvidenceRef(
            schema_version="evidence-ref/v1",
            evidence_id="evidence-example",
            evidence_type="observation",
            artifact_refs=(" ",),
        )


def test_optional_text_must_not_be_blank_when_present() -> None:
    with pytest.raises(ValueError, match="statement"):
        ClaimRef(
            schema_version="claim-ref/v1",
            claim_id="claim-example",
            claim_type="assertion",
            statement=" ",
        )


def test_reference_contracts_ignore_temporal_provenance_and_resolution_metadata() -> None:
    evidence = EvidenceRef.from_dict(
        {
            "schema_version": "evidence-ref/v1",
            "evidence_id": "evidence-boundary",
            "evidence_type": "observation",
            "known_at": "2026-10-21T11:05:00Z",
            "source_trust": 0.95,
            "confidence": 0.25,
            "supersedes_ref": "evidence:old",
            "resolution_state": "STALE",
        }
    )
    claim = ClaimRef.from_dict(
        {
            "schema_version": "claim-ref/v1",
            "claim_id": "claim-boundary",
            "claim_type": "assertion",
            "valid_from": "2026-10-01T00:00:00Z",
            "source_span": {"start": 0, "end": 7},
            "source_trust": 0.1,
            "confidence": 0.9,
            "superseded_by_ref": "claim:new",
        }
    )

    assert evidence.to_dict() == {
        "schema_version": "evidence-ref/v1",
        "evidence_id": "evidence-boundary",
        "evidence_type": "observation",
        "source_refs": [],
        "artifact_refs": [],
        "claim_refs": [],
        "decision_refs": [],
    }
    assert claim.to_dict() == {
        "schema_version": "claim-ref/v1",
        "claim_id": "claim-boundary",
        "claim_type": "assertion",
        "evidence_refs": [],
        "artifact_refs": [],
        "decision_refs": [],
        "source_refs": [],
    }
