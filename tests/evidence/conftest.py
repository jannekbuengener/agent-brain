"""Shared fixtures for slice 8 evidence tests."""

from __future__ import annotations

from datetime import datetime

from agent_brain.contracts import (
    ClaimRef,
    EvidenceRef,
    Provenance,
    ResolutionMeta,
    TemporalEnvelope,
)
from agent_brain.evidence.contract import (
    CLAIM_STATE_SCHEMA,
    DECISION_RECORD_SCHEMA,
    EVIDENCE_STATE_SCHEMA,
    ClaimState,
    DecisionRecord,
    EvidenceState,
)

_KNOWN = datetime(2026, 1, 15, 12, 0, 0)


def temporal(**kwargs: datetime | None) -> TemporalEnvelope:
    return TemporalEnvelope(
        schema_version="temporal-envelope/v1",
        known_at=kwargs.get("known_at", _KNOWN),
        valid_from=kwargs.get("valid_from"),
        valid_until=kwargs.get("valid_until"),
        system_as_of=kwargs.get("system_as_of"),
    )


def provenance(source_ref: str, source_hash: str | None = None) -> Provenance:
    return Provenance(
        schema_version="provenance/v1",
        source_kind="repository",
        source_ref=source_ref,
        source_hash=source_hash,
    )


def resolution_meta(**kwargs: object) -> ResolutionMeta:
    return ResolutionMeta(
        schema_version="resolution-meta/v1",
        supersedes_ref=kwargs.get("supersedes_ref"),
        superseded_by_ref=kwargs.get("superseded_by_ref"),
        supersession_reason=kwargs.get("supersession_reason"),
        source_trust=kwargs.get("source_trust"),
        confidence=kwargs.get("confidence"),
    )


def evidence_ref(evidence_id: str = "evidence-1") -> EvidenceRef:
    return EvidenceRef(
        schema_version="evidence-ref/v1",
        evidence_id=evidence_id,
        evidence_type="test",
    )


def claim_ref(claim_id: str = "claim-1", evidence_ids: tuple[str, ...] = ()) -> ClaimRef:
    return ClaimRef(
        schema_version="claim-ref/v1",
        claim_id=claim_id,
        claim_type="behavior",
        statement="neutral claim",
        evidence_refs=evidence_ids,
    )


def evidence_state(
    evidence_id: str = "evidence-1",
    *,
    source_ref: str = "source-a",
    source_hash: str | None = "a" * 64,
    strength: str = "moderate",
    envelope: TemporalEnvelope | None = None,
    resolution: ResolutionMeta | None = None,
) -> EvidenceState:
    return EvidenceState(
        schema_version=EVIDENCE_STATE_SCHEMA,
        evidence_id=evidence_id,
        temporal=envelope or temporal(),
        provenance=provenance(source_ref, source_hash),
        resolution_meta=resolution or resolution_meta(source_trust=0.8, confidence=0.7),
        strength=strength,
        status="active",
    )


def claim_state(claim_id: str = "claim-1", status: str = "supported") -> ClaimState:
    return ClaimState(
        schema_version=CLAIM_STATE_SCHEMA,
        claim_id=claim_id,
        temporal=temporal(),
        provenance=provenance("source-a", "a" * 64),
        resolution_meta=resolution_meta(),
        status=status,
        scope="neutral-scope",
    )


def decision_record(
    decision_id: str = "decision-1",
    *,
    resolution: ResolutionMeta | None = None,
) -> DecisionRecord:
    return DecisionRecord(
        schema_version=DECISION_RECORD_SCHEMA,
        decision_id=decision_id,
        temporal=temporal(),
        provenance=provenance("source-a"),
        resolution_meta=resolution or resolution_meta(),
        title="title",
        question="question",
        answer="answer",
        decision_type="choice",
        status="accepted",
    )
