"""Contradiction detection and cross-provenance conflict materialization."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from agent_brain.core.canonical import canonical_hash

from agent_brain.evidence.contract import (
    CONTRADICTION_FINDING_SCHEMA,
    CONTRADICTION_SCAN_RESULT_SCHEMA,
    CONTRADICTION_TYPES,
    ClaimResolution,
    ClaimState,
    ContradictionError,
    ContradictionFinding,
    ContradictionScanResult,
    DecisionRecord,
    EvidenceResolution,
    EvidenceState,
    SEVERITY_LEVELS,
)

_DEFAULT_LIMITATIONS = (
    "Contradiction findings are informational; they do not grant authorization.",
)


@dataclass(frozen=True, slots=True)
class ContradictionBundle:
    claims: tuple = ()
    claim_states: tuple = ()
    evidence: tuple = ()
    evidence_states: tuple = ()
    decisions: tuple = ()
    evidence_resolution: EvidenceResolution | None = None
    claim_resolution: ClaimResolution | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.claims, tuple):
            raise ContradictionError("claims must be a tuple")
        if not isinstance(self.evidence, tuple):
            raise ContradictionError("evidence must be a tuple")
        if not isinstance(self.decisions, tuple):
            raise ContradictionError("decisions must be a tuple")


@dataclass(frozen=True, slots=True)
class ContradictionRule:
    rule_id: str
    rule_type: str
    severity: str
    confidence: float
    description: str
    recommendation: str
    detector: Callable[[ContradictionBundle], tuple[tuple[str, ...], ...]]

    def __post_init__(self) -> None:
        if self.rule_type not in CONTRADICTION_TYPES:
            raise ContradictionError(f"unsupported rule_type: {self.rule_type}")
        if self.severity not in SEVERITY_LEVELS:
            raise ContradictionError(f"unsupported severity: {self.severity}")


@dataclass(frozen=True, slots=True)
class ContradictionRuleSet:
    rules: tuple[ContradictionRule, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.rules, tuple) or not self.rules:
            raise ContradictionError("rules must be a non-empty tuple")


def _finding_id(rule_id: str, rule_type: str, refs: tuple[str, ...]) -> str:
    payload = {"rule_id": rule_id, "rule_type": rule_type, "refs": sorted(refs)}
    return canonical_hash(payload)[:16]


def _detect_cross_provenance(bundle: ContradictionBundle) -> tuple[tuple[str, ...], ...]:
    groups: list[tuple[str, ...]] = []
    if bundle.evidence_resolution is not None:
        groups.extend(bundle.evidence_resolution.conflicting_evidence_ids)
    if bundle.claim_resolution is not None:
        groups.extend(bundle.claim_resolution.conflicting_claim_ids)
    return tuple(groups)


def _detect_claim_vs_evidence(bundle: ContradictionBundle) -> tuple[tuple[str, ...], ...]:
    matches: list[tuple[str, ...]] = []
    states = {state.claim_id: state for state in bundle.claim_states if isinstance(state, ClaimState)}
    for claim in bundle.claims:
        state = states.get(getattr(claim, "claim_id", ""))
        if state is None:
            continue
        if state.status in {"supported", "weakly_supported"} and not claim.evidence_refs:
            matches.append((claim.claim_id,))
    return tuple(matches)


def _detect_decision_vs_evidence(bundle: ContradictionBundle) -> tuple[tuple[str, ...], ...]:
    matches: list[tuple[str, ...]] = []
    for decision in bundle.decisions:
        if not isinstance(decision, DecisionRecord):
            continue
        if decision.requires_evidence and not decision.evidence_refs:
            matches.append((decision.decision_id,))
    return tuple(matches)


def _detect_stale_decision_vs_new_evidence(bundle: ContradictionBundle) -> tuple[tuple[str, ...], ...]:
    matches: list[tuple[str, ...]] = []
    evidence_known_at = {
        state.evidence_id: state.temporal.known_at
        for state in bundle.evidence_states
        if isinstance(state, EvidenceState)
    }
    for decision in bundle.decisions:
        if not isinstance(decision, DecisionRecord):
            continue
        decision_known = decision.temporal.known_at
        for evidence_id in decision.evidence_refs:
            evidence_at = evidence_known_at.get(evidence_id)
            if evidence_at is not None and evidence_at > decision_known:
                matches.append((decision.decision_id, evidence_id))
    return tuple(matches)


def default_contradiction_rule_set() -> ContradictionRuleSet:
    return ContradictionRuleSet(
        rules=(
            ContradictionRule(
                rule_id="claim-vs-evidence-default",
                rule_type="claim_vs_evidence",
                severity="warning",
                confidence=0.7,
                description="Claim status requires evidence but none is linked.",
                recommendation="review",
                detector=_detect_claim_vs_evidence,
            ),
            ContradictionRule(
                rule_id="decision-vs-evidence-default",
                rule_type="decision_vs_evidence",
                severity="warning",
                confidence=0.7,
                description="Decision requires evidence but none is linked.",
                recommendation="review",
                detector=_detect_decision_vs_evidence,
            ),
            ContradictionRule(
                rule_id="stale-decision-vs-new-evidence-default",
                rule_type="stale_decision_vs_new_evidence",
                severity="warning",
                confidence=0.6,
                description="Decision predates linked evidence.",
                recommendation="recheck_decision",
                detector=_detect_stale_decision_vs_new_evidence,
            ),
            ContradictionRule(
                rule_id="cross-provenance-conflict-default",
                rule_type="cross_provenance_conflict",
                severity="blocking",
                confidence=1.0,
                description="Cross-provenance conflict detected.",
                recommendation="manual_review",
                detector=_detect_cross_provenance,
            ),
        )
    )


def detect_contradictions(
    *,
    bundle: ContradictionBundle,
    rules: ContradictionRuleSet | None = None,
    as_of: datetime,
) -> ContradictionScanResult:
    if not isinstance(bundle, ContradictionBundle):
        raise ContradictionError("bundle must be a ContradictionBundle")
    if not isinstance(as_of, datetime):
        raise ContradictionError("as_of must be a datetime")
    rule_set = rules or default_contradiction_rule_set()
    findings: list[ContradictionFinding] = []
    for rule in rule_set.rules:
        for refs in rule.detector(bundle):
            finding_id = _finding_id(rule.rule_id, rule.rule_type, refs)
            findings.append(
                ContradictionFinding(
                    schema_version=CONTRADICTION_FINDING_SCHEMA,
                    finding_id=finding_id,
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    status="open",
                    detected_at=as_of,
                    explanation=rule.description,
                    recommendation=rule.recommendation,
                )
            )
    findings.sort(key=lambda item: (item.severity, item.rule_type, item.finding_id))
    blocking_count = sum(1 for item in findings if item.severity == "blocking")
    return ContradictionScanResult(
        schema_version=CONTRADICTION_SCAN_RESULT_SCHEMA,
        findings=tuple(findings),
        blocking_count=blocking_count,
        warnings=(),
        limitations=_DEFAULT_LIMITATIONS,
    )
