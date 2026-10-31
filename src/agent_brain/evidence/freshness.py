"""Freshness evaluation and ResolutionState derivation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from agent_brain.contracts import ResolutionState
from agent_brain.core.canonical import canonical_hash
from agent_brain.evidence.contract import (
    FRESHNESS_REPORT_SCHEMA,
    RESOLUTION_STATE_ENTRY_SCHEMA,
    STALE_FINDING_SCHEMA,
    ArtifactState,
    ClaimState,
    DecisionRecord,
    EvidenceState,
    FreshnessError,
    FreshnessPolicy,
    FreshnessReport,
    ResolutionStateEntry,
    SourceState,
    StaleFinding,
)

_DEFAULT_LIMITATIONS = (
    "Freshness findings are informational; they do not grant authorization.",
)

_STATE_PRECEDENCE = {
    ResolutionState.UNKNOWN: 3,
    ResolutionState.SUPERSEDED: 2,
    ResolutionState.STALE: 1,
    ResolutionState.CURRENT: 0,
}


@dataclass(frozen=True, slots=True)
class FreshnessBundle:
    evidence_states: tuple[EvidenceState, ...] = ()
    claim_states: tuple[ClaimState, ...] = ()
    decision_records: tuple[DecisionRecord, ...] = ()
    expected_sources: tuple[SourceState, ...] = ()
    observed_sources: tuple[SourceState, ...] = ()
    artifacts: tuple[ArtifactState, ...] = ()
    expected_dependency_edge_ids: tuple[str, ...] = ()
    observed_dependency_edge_ids: tuple[str, ...] = ()
    conflicting_evidence_ids: tuple[tuple[str, ...], ...] = ()
    conflicting_claim_ids: tuple[tuple[str, ...], ...] = ()
    known_entity_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name, value in (
            ("evidence_states", self.evidence_states),
            ("claim_states", self.claim_states),
            ("decision_records", self.decision_records),
        ):
            if not isinstance(value, tuple):
                raise FreshnessError(f"{field_name} must be a tuple")


def _pick_state(candidates: list[tuple[ResolutionState, str, str]]) -> tuple[ResolutionState, str, str]:
    if not candidates:
        return ResolutionState.CURRENT, "current", "No temporal conflict detected."
    best = max(candidates, key=lambda item: _STATE_PRECEDENCE[item[0]])
    return best


def _derive_for_temporal(
    *,
    ref: str,
    entity_kind: str,
    temporal,
    resolution_meta,
    as_of: datetime,
    in_conflict: bool,
    known_ids: set[str],
) -> ResolutionStateEntry:
    candidates: list[tuple[ResolutionState, str, str]] = []
    if temporal.known_at > as_of:
        candidates.append((ResolutionState.UNKNOWN, "not_yet_known", "known_at is after as_of"))
    if temporal.valid_from is not None and temporal.valid_from > as_of:
        candidates.append((ResolutionState.UNKNOWN, "not_yet_valid", "valid_from is after as_of"))
    if in_conflict:
        candidates.append(
            (
                ResolutionState.UNKNOWN,
                "cross_provenance_conflict",
                "Entity participates in a cross-provenance conflict group.",
            )
        )
    target = resolution_meta.superseded_by_ref
    if target:
        if target in known_ids:
            candidates.append((ResolutionState.SUPERSEDED, "superseded_by_ref", f"Superseded by {target}"))
        else:
            candidates.append(
                (
                    ResolutionState.UNKNOWN,
                    "broken_supersession_chain",
                    "superseded_by_ref target is unknown.",
                )
            )
    if temporal.valid_until is not None and temporal.valid_until <= as_of:
        candidates.append((ResolutionState.STALE, "validity_window_closed", "valid_until is before as_of"))
    state, reason, explanation = _pick_state(candidates)
    return ResolutionStateEntry(
        schema_version=RESOLUTION_STATE_ENTRY_SCHEMA,
        ref=ref,
        entity_kind=entity_kind,
        resolution_state=state,
        reason_code=reason,
        explanation=explanation,
    )


def _stale_id(stale_type: str, entity_ref: str) -> str:
    return canonical_hash({"stale_type": stale_type, "entity_ref": entity_ref})[:16]


def evaluate_freshness(
    *,
    bundle: FreshnessBundle,
    policy: FreshnessPolicy | None = None,
    as_of: datetime,
) -> FreshnessReport:
    if not isinstance(bundle, FreshnessBundle):
        raise FreshnessError("bundle must be a FreshnessBundle")
    if not isinstance(as_of, datetime):
        raise FreshnessError("as_of must be a datetime")
    if policy is None:
        policy = FreshnessPolicy.default()

    warnings: list[str] = []
    limitations = list(_DEFAULT_LIMITATIONS)
    stale_findings: list[StaleFinding] = []
    refresh: set[str] = set()
    known_ids = set(bundle.known_entity_ids)
    known_ids.update(state.evidence_id for state in bundle.evidence_states)
    known_ids.update(state.claim_id for state in bundle.claim_states)
    known_ids.update(record.decision_id for record in bundle.decision_records)

    conflict_evidence = {item for group in bundle.conflicting_evidence_ids for item in group}
    conflict_claims = {item for group in bundle.conflicting_claim_ids for item in group}

    expected = {item.source_ref: item for item in bundle.expected_sources}
    observed = {item.source_ref: item for item in bundle.observed_sources}
    for source_ref, expected_source in expected.items():
        observed_source = observed.get(source_ref)
        if observed_source is None:
            if expected_source.observed is False:
                stale_findings.append(
                    StaleFinding(
                        schema_version=STALE_FINDING_SCHEMA,
                        finding_id=_stale_id("source_deleted", source_ref),
                        stale_type="source_deleted",
                        severity="warning",
                        status="open",
                        detected_at=as_of,
                        entity_ref=source_ref,
                        explanation="Expected source is no longer observed.",
                    )
                )
                refresh.add("reverify_source")
            else:
                warnings.append(f"missing_source_observation:{source_ref}")
            continue
        if (
            expected_source.source_hash
            and observed_source.source_hash
            and expected_source.source_hash != observed_source.source_hash
        ):
            stale_findings.append(
                StaleFinding(
                    schema_version=STALE_FINDING_SCHEMA,
                    finding_id=_stale_id("source_hash_changed", source_ref),
                    stale_type="source_hash_changed",
                    severity="warning",
                    status="open",
                    detected_at=as_of,
                    entity_ref=source_ref,
                    explanation="Observed source hash differs from expected hash.",
                )
            )
            refresh.add("reverify_source")

    for state in bundle.evidence_states:
        if state.temporal.valid_until is not None and state.temporal.valid_until <= as_of:
            stale_findings.append(
                StaleFinding(
                    schema_version=STALE_FINDING_SCHEMA,
                    finding_id=_stale_id("validity_window_closed", state.evidence_id),
                    stale_type="validity_window_closed",
                    severity="warning",
                    status="open",
                    detected_at=as_of,
                    entity_ref=state.evidence_id,
                    explanation="Evidence validity window is closed.",
                )
            )
            refresh.add("refresh_evidence")

    window = timedelta(seconds=policy.default_freshness_window_seconds)
    for artifact in bundle.artifacts:
        age = as_of - artifact.temporal.known_at
        stale_type = None
        if artifact.artifact_type == "context_package":
            stale_type = "stale_context_package"
            refresh.add("rebuild_context_package")
        elif artifact.artifact_type == "briefing":
            stale_type = "stale_briefing"
            refresh.add("regenerate_briefing")
        if stale_type and age > window:
            stale_findings.append(
                StaleFinding(
                    schema_version=STALE_FINDING_SCHEMA,
                    finding_id=_stale_id(stale_type, artifact.ref.artifact_id),
                    stale_type=stale_type,
                    severity="warning",
                    status="open",
                    detected_at=as_of,
                    entity_ref=artifact.ref.artifact_id,
                    explanation=f"Artifact exceeded freshness window ({policy.default_freshness_window_seconds}s).",
                )
            )

    expected_edges = set(bundle.expected_dependency_edge_ids)
    observed_edges = set(bundle.observed_dependency_edge_ids)
    for edge_id in sorted(expected_edges - observed_edges):
        stale_findings.append(
            StaleFinding(
                schema_version=STALE_FINDING_SCHEMA,
                finding_id=_stale_id("dependency_edge_no_longer_observed", edge_id),
                stale_type="dependency_edge_no_longer_observed",
                severity="warning",
                status="open",
                detected_at=as_of,
                entity_ref=edge_id,
                explanation="Expected dependency edge is no longer observed.",
            )
        )
        refresh.add("reobserve_dependency_edge")

    resolution_states: list[ResolutionStateEntry] = []
    for state in bundle.evidence_states:
        resolution_states.append(
            _derive_for_temporal(
                ref=state.evidence_id,
                entity_kind="evidence",
                temporal=state.temporal,
                resolution_meta=state.resolution_meta,
                as_of=as_of,
                in_conflict=state.evidence_id in conflict_evidence,
                known_ids=known_ids,
            )
        )
    for state in bundle.claim_states:
        resolution_states.append(
            _derive_for_temporal(
                ref=state.claim_id,
                entity_kind="claim",
                temporal=state.temporal,
                resolution_meta=state.resolution_meta,
                as_of=as_of,
                in_conflict=state.claim_id in conflict_claims,
                known_ids=known_ids,
            )
        )
    for record in bundle.decision_records:
        resolution_states.append(
            _derive_for_temporal(
                ref=record.decision_id,
                entity_kind="decision",
                temporal=record.temporal,
                resolution_meta=record.resolution_meta,
                as_of=as_of,
                in_conflict=False,
                known_ids=known_ids,
            )
        )

    resolution_states.sort(key=lambda item: (item.entity_kind, item.ref))
    stale_findings.sort(key=lambda item: (item.stale_type, item.finding_id))
    system_as_of = None
    for state in bundle.evidence_states:
        if state.temporal.system_as_of is not None:
            system_as_of = state.temporal.system_as_of
            break

    if not refresh:
        refresh.add("manual_review")

    return FreshnessReport(
        schema_version=FRESHNESS_REPORT_SCHEMA,
        stale_findings=tuple(stale_findings),
        resolution_states=tuple(resolution_states),
        recommended_refresh=tuple(sorted(refresh)),
        system_as_of=system_as_of,
        warnings=tuple(sorted(set(warnings))),
        limitations=tuple(limitations),
    )
