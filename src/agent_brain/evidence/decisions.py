"""Decision history and replay."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from agent_brain.core.canonical import canonical_hash
from agent_brain.evidence.contract import (
    DECISION_HISTORY_RESULT_SCHEMA,
    DECISION_REPLAY_SCHEMA,
    DecisionError,
    DecisionHistoryResult,
    DecisionQuery,
    DecisionRecord,
    DecisionReplay,
    DecisionReplayQuery,
)

_DEFAULT_LIMITATIONS = (
    "Decision replay is explanatory only; it does not grant authorization.",
)


def _sort_records(records: Sequence[DecisionRecord]) -> list[DecisionRecord]:
    def key(record: DecisionRecord) -> tuple[int, str, str]:
        known_at = record.temporal.known_at
        return (0, known_at.isoformat(), record.decision_id)

    return sorted(records, key=key)


def _build_chain(
    records_by_id: Mapping[str, DecisionRecord],
    start_id: str,
) -> tuple[tuple[str, ...], list[str]]:
    chain: list[str] = []
    warnings: list[str] = []
    visited: set[str] = set()
    current = start_id
    while current and current not in visited:
        visited.add(current)
        chain.append(current)
        record = records_by_id.get(current)
        if record is None:
            break
        nxt = record.resolution_meta.superseded_by_ref
        if not nxt:
            break
        current = nxt
        if current in visited:
            warnings.append(f"supersession_cycle:{start_id}")
            break
    return tuple(chain), warnings


def query_decision_history(
    *,
    decisions: Sequence[DecisionRecord],
    query: DecisionQuery,
    known_evidence_ids: Sequence[str] | None = None,
    known_claim_ids: Sequence[str] | None = None,
) -> DecisionHistoryResult:
    warnings: list[str] = []
    limitations = list(_DEFAULT_LIMITATIONS)
    records = _sort_records(decisions)
    records_by_id = {record.decision_id: record for record in records}

    if known_evidence_ids is None or known_claim_ids is None:
        warnings.append("resolution_inputs_not_provided")
        limitations.append("Evidence and claim resolution inputs were not provided.")

    evidence_ids = set(known_evidence_ids or ())
    claim_ids = set(known_claim_ids or ())

    current: list[str] = []
    superseded: list[str] = []
    invalidated: list[str] = []
    unresolved: list[str] = []
    chains: list[tuple[str, ...]] = []
    unresolved_evidence: set[str] = set()
    unresolved_claims: set[str] = set()

    for record in records:
        for evidence_id in record.evidence_refs:
            if evidence_ids and evidence_id not in evidence_ids:
                unresolved_evidence.add(evidence_id)
        for claim_id in record.claim_refs:
            if claim_ids and claim_id not in claim_ids:
                unresolved_claims.add(claim_id)

        target = record.resolution_meta.superseded_by_ref
        if record.status == "invalidated":
            invalidated.append(record.decision_id)
        elif target:
            if target in records_by_id:
                superseded.append(record.decision_id)
            else:
                unresolved.append(record.decision_id)
                warnings.append(f"broken_supersession_chain:{record.decision_id}")
        else:
            current.append(record.decision_id)

        chain, chain_warnings = _build_chain(records_by_id, record.decision_id)
        chains.append(chain)
        warnings.extend(chain_warnings)

    return DecisionHistoryResult(
        schema_version=DECISION_HISTORY_RESULT_SCHEMA,
        current_decision_ids=tuple(current),
        superseded_decision_ids=tuple(superseded),
        invalidated_decision_ids=tuple(invalidated),
        unresolved_decision_ids=tuple(unresolved),
        supersession_chains=tuple(chains),
        unresolved_evidence_refs=tuple(sorted(unresolved_evidence)),
        unresolved_claim_refs=tuple(sorted(unresolved_claims)),
        warnings=tuple(sorted(set(warnings))),
        limitations=tuple(limitations),
    )


def build_decision_replay(
    *,
    decisions: Sequence[DecisionRecord],
    query: DecisionReplayQuery,
    as_of: datetime,
    known_evidence_ids: Sequence[str] | None = None,
    known_claim_ids: Sequence[str] | None = None,
    evidence_summaries: Mapping[str, str] | None = None,
    claim_summaries: Mapping[str, str] | None = None,
) -> DecisionReplay:
    if not isinstance(as_of, datetime):
        raise DecisionError("as_of must be a datetime")
    records_by_id = {record.decision_id: record for record in decisions}
    if query.decision_id not in records_by_id:
        raise DecisionError(f"unknown decision_id: {query.decision_id}")

    chain, _warnings = _build_chain(records_by_id, query.decision_id)
    payload = {"chain": list(chain), "decision_id": query.decision_id}
    decision_chain_hash = canonical_hash(payload)

    record = records_by_id[query.decision_id]
    unresolved_evidence: set[str] = set()
    unresolved_claims: set[str] = set()
    if known_evidence_ids is not None:
        for evidence_id in record.evidence_refs:
            if evidence_id not in set(known_evidence_ids):
                unresolved_evidence.add(evidence_id)
    else:
        unresolved_evidence.update(record.evidence_refs)
    if known_claim_ids is not None:
        for claim_id in record.claim_refs:
            if claim_id not in set(known_claim_ids):
                unresolved_claims.add(claim_id)
    else:
        unresolved_claims.update(record.claim_refs)

    return DecisionReplay(
        schema_version=DECISION_REPLAY_SCHEMA,
        decision_id=query.decision_id,
        chain=chain,
        decision_chain_hash=decision_chain_hash,
        authorization_implied=False,
        authorization_refs=record.authorization_refs,
        unresolved_evidence_refs=tuple(sorted(unresolved_evidence)),
        unresolved_claim_refs=tuple(sorted(unresolved_claims)),
        limitations=_DEFAULT_LIMITATIONS,
        as_of=as_of,
    )
