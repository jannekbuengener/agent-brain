"""Evidence and claim resolution without temporal evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from types import MappingProxyType

from agent_brain.contracts import ClaimRef, EvidenceRef

from agent_brain.evidence.contract import (
    CLAIM_RESOLUTION_SCHEMA,
    EVIDENCE_RESOLUTION_SCHEMA,
    ClaimQuery,
    ClaimResolution,
    ClaimResolutionPolicy,
    ClaimState,
    EvidenceQuery,
    EvidenceResolution,
    EvidenceResolutionPolicy,
    EvidenceState,
    ResolutionError,
)

_DEFAULT_LIMITATIONS = (
    "Resolution is informational only; it does not grant authorization.",
)


def _sort_key(
    *,
    known_at: datetime | None,
    entity_id: str,
) -> tuple[int, str, str]:
    if known_at is None:
        return (1, "", entity_id)
    return (0, known_at.isoformat(), entity_id)


def _index_states(states: Sequence[EvidenceState | ClaimState]) -> dict[str, list]:
    grouped: dict[str, list] = defaultdict(list)
    for state in states:
        entity_id = getattr(state, "evidence_id", None) or getattr(state, "claim_id")
        grouped[str(entity_id)].append(state)
    return grouped


def _supersession_linked(a_meta, b_meta, a_id: str, b_id: str) -> bool:
    if a_meta.supersedes_ref == b_id or a_meta.superseded_by_ref == b_id:
        return True
    if b_meta.supersedes_ref == a_id or b_meta.superseded_by_ref == a_id:
        return True
    return False


def _provenance_conflict(a: EvidenceState | ClaimState, b: EvidenceState | ClaimState) -> bool:
    a_id = getattr(a, "evidence_id", None) or getattr(a, "claim_id")
    b_id = getattr(b, "evidence_id", None) or getattr(b, "claim_id")
    if _supersession_linked(a.resolution_meta, b.resolution_meta, a_id, b_id):
        return False
    a_ref = a.provenance.source_ref
    b_ref = b.provenance.source_ref
    a_hash = a.provenance.source_hash
    b_hash = b.provenance.source_hash
    if a_ref != b_ref:
        return True
    if a_hash and b_hash and a_hash != b_hash:
        return True
    if not a_hash or not b_hash:
        return True
    return False


def _conflict_groups(states: Sequence[EvidenceState | ClaimState]) -> tuple[tuple[str, ...], ...]:
    by_id: dict[str, list[EvidenceState | ClaimState]] = defaultdict(list)
    for state in states:
        entity_id = getattr(state, "evidence_id", None) or getattr(state, "claim_id")
        by_id[str(entity_id)].append(state)
    groups: list[tuple[str, ...]] = []
    for entity_id, candidates in sorted(by_id.items()):
        if len(candidates) < 2:
            continue
        conflict = False
        for index, left in enumerate(candidates):
            for right in candidates[index + 1 :]:
                if _provenance_conflict(left, right):
                    conflict = True
                    break
            if conflict:
                break
        if conflict:
            groups.append(tuple(sorted({getattr(item, "evidence_id", None) or getattr(item, "claim_id") for item in candidates})))
    return tuple(groups)


def _match_evidence(
    evidence: EvidenceRef,
    state: EvidenceState | None,
    query: EvidenceQuery,
) -> bool:
    if query.mode == "by_evidence_id":
        return evidence.evidence_id == query.evidence_id
    if query.mode == "by_artifact":
        return query.artifact in evidence.artifact_refs
    if query.mode == "by_claim":
        return query.claim in evidence.claim_refs
    if query.mode == "by_decision":
        return query.decision in evidence.decision_refs
    if query.mode == "by_source":
        return query.source in evidence.source_refs
    if query.mode == "by_evidence_type":
        return evidence.evidence_type == query.evidence_type
    if query.mode == "by_strength":
        return state is not None and state.strength == query.strength
    if query.mode == "by_status":
        return state is not None and state.status == query.status
    return False


def resolve_evidence(
    *,
    evidence: Sequence[EvidenceRef],
    states: Sequence[EvidenceState] = (),
    query: EvidenceQuery | None = None,
    policy: EvidenceResolutionPolicy | None = None,
) -> EvidenceResolution:
    if policy is None:
        policy = EvidenceResolutionPolicy.default()
    warnings: list[str] = []
    limitations = list(_DEFAULT_LIMITATIONS)
    state_index = _index_states(states)
    known_ids = {item.evidence_id for item in evidence}
    for entity_id, overlays in state_index.items():
        if entity_id not in known_ids:
            warnings.append(f"orphan_evidence_state:{entity_id}")

    records: list[tuple[EvidenceRef, EvidenceState | None, datetime | None]] = []
    for ref in evidence:
        if not ref.evidence_id:
            raise ResolutionError("evidence record missing evidence_id")
        overlay_list = state_index.get(ref.evidence_id, [])
        overlay = overlay_list[0] if overlay_list else None
        known_at = overlay.temporal.known_at if overlay is not None else None
        records.append((ref, overlay, known_at))

    records.sort(key=lambda item: _sort_key(known_at=item[2], entity_id=item[0].evidence_id))

    matched: list[str] = []
    by_status: dict[str, list[str]] = defaultdict(list)
    by_strength: dict[str, list[str]] = defaultdict(list)
    for ref, overlay, _known_at in records:
        if query is not None and not _match_evidence(ref, overlay, query):
            continue
        strength = overlay.strength if overlay is not None else policy.default_strength
        status = overlay.status if overlay is not None else "unknown"
        matched.append(ref.evidence_id)
        by_status[status].append(ref.evidence_id)
        by_strength[strength].append(ref.evidence_id)
        if len(matched) >= (query.limit if query is not None else len(records)):
            break

    conflicting = _conflict_groups(states)
    return EvidenceResolution(
        schema_version=EVIDENCE_RESOLUTION_SCHEMA,
        matched_evidence_ids=tuple(matched),
        by_status=MappingProxyType({key: tuple(value) for key, value in sorted(by_status.items())}),
        by_strength=MappingProxyType({key: tuple(value) for key, value in sorted(by_strength.items())}),
        conflicting_evidence_ids=conflicting,
        warnings=tuple(sorted(set(warnings))),
        limitations=tuple(limitations),
    )


def _match_claim(
    claim: ClaimRef,
    state: ClaimState | None,
    query: ClaimQuery,
) -> bool:
    if query.mode == "by_claim_id":
        return claim.claim_id == query.claim_id
    if query.mode == "by_topic":
        return state is not None and query.topic in state.topics
    if query.mode == "by_scope":
        return state is not None and state.scope == query.scope
    if query.mode == "by_status":
        return state is not None and state.status == query.status
    if query.mode == "by_artifact":
        return query.artifact in claim.artifact_refs
    if query.mode == "by_evidence_ref":
        return query.evidence_ref in claim.evidence_refs
    if query.mode == "by_decision_ref":
        return query.decision_ref in claim.decision_refs
    return False


def resolve_claims(
    *,
    claims: Sequence[ClaimRef],
    states: Sequence[ClaimState] = (),
    evidence: Sequence[EvidenceRef] = (),
    query: ClaimQuery | None = None,
    policy: ClaimResolutionPolicy | None = None,
) -> ClaimResolution:
    if policy is None:
        policy = ClaimResolutionPolicy.default()
    warnings: list[str] = []
    limitations = list(_DEFAULT_LIMITATIONS)
    evidence_ids = {item.evidence_id for item in evidence}
    state_index = _index_states(states)
    known_claim_ids = {item.claim_id for item in claims}
    for entity_id, overlays in state_index.items():
        if entity_id not in known_claim_ids:
            warnings.append(f"orphan_claim_state:{entity_id}")

    records: list[tuple[ClaimRef, ClaimState | None, datetime | None]] = []
    for ref in claims:
        if not ref.claim_id:
            raise ResolutionError("claim record missing claim_id")
        overlay = state_index.get(ref.claim_id, [None])[0]
        if overlay is None:
            warnings.append(f"claim_without_state_overlay:{ref.claim_id}")
        known_at = overlay.temporal.known_at if overlay is not None else None
        records.append((ref, overlay, known_at))
    records.sort(key=lambda item: _sort_key(known_at=item[2], entity_id=item[0].claim_id))

    matched: list[str] = []
    by_status: dict[str, list[str]] = defaultdict(list)
    disputed: list[str] = []
    invalidated: list[str] = []
    missing_evidence: list[str] = []
    unresolved_refs: set[str] = set()

    for ref, overlay, _known_at in records:
        if query is not None and not _match_claim(ref, overlay, query):
            continue
        status = overlay.status if overlay is not None else "unknown"
        matched.append(ref.claim_id)
        by_status[status].append(ref.claim_id)
        if status in policy.blocking_statuses:
            if status == "disputed":
                disputed.append(ref.claim_id)
            if status == "invalidated":
                invalidated.append(ref.claim_id)
        if status in policy.statuses_requiring_evidence:
            resolved = [evidence_id for evidence_id in ref.evidence_refs if evidence_id in evidence_ids]
            if not resolved:
                missing_evidence.append(ref.claim_id)
            for evidence_id in ref.evidence_refs:
                if evidence_id not in evidence_ids:
                    unresolved_refs.add(evidence_id)
        if len(matched) >= (query.limit if query is not None else len(records)):
            break

    conflicting = _conflict_groups(states)
    return ClaimResolution(
        schema_version=CLAIM_RESOLUTION_SCHEMA,
        matched_claim_ids=tuple(matched),
        by_status=MappingProxyType({key: tuple(value) for key, value in sorted(by_status.items())}),
        disputed_claim_ids=tuple(sorted(disputed)),
        invalidated_claim_ids=tuple(sorted(invalidated)),
        missing_evidence_claim_ids=tuple(sorted(missing_evidence)),
        unresolved_evidence_refs=tuple(sorted(unresolved_refs)),
        conflicting_claim_ids=conflicting,
        warnings=tuple(sorted(set(warnings))),
        limitations=tuple(limitations),
    )
