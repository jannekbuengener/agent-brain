"""Provenance gate for Memory read (#11).

Required fields come from the existing #37 ``Provenance`` contract:
``source_kind`` and ``source_ref`` (always present on a constructed Provenance).

Additional load-bearing requirements for Memory context:
- at least one evidence_ref on the MemoryRecord, OR provenance.derived_from
  non-empty (structured lineage)
- provenance.source_kind and source_ref non-blank (enforced by Provenance)

Missing required metadata → not admissible; derived state UNKNOWN with an
explicit reason. MISSING_METADATA != TRUSTED.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_brain.contracts.resolution import ResolutionState
from agent_brain.memory.read.models import MemoryEntry


@dataclass(frozen=True, slots=True)
class ProvenanceGateResult:
    """Gate outcome. Failures never silently become CURRENT."""

    passed: bool
    reason_codes: tuple[str, ...]
    forced_state: ResolutionState | None
    explanation: str


def evaluate_provenance_gate(entry: MemoryEntry) -> ProvenanceGateResult:
    """Return whether ``entry`` may proceed as load-bearing Memory context."""
    if not isinstance(entry, MemoryEntry):
        raise TypeError("entry must be a MemoryEntry")

    reasons: list[str] = []
    provenance = entry.provenance
    record = entry.record

    if not provenance.source_kind.strip():
        reasons.append("missing_source_kind")
    if not provenance.source_ref.strip():
        reasons.append("missing_source_ref")

    has_evidence = bool(record.evidence_refs)
    has_lineage = bool(provenance.derived_from)
    if not has_evidence and not has_lineage:
        reasons.append("missing_evidence_or_lineage")

    # Confidence / source_trust are optional on ResolutionMeta; absence must not
    # be treated as TRUSTED. We surface a soft limitation reason but do not
    # alone force UNKNOWN — only hard provenance failures do.
    soft: list[str] = []
    if entry.resolution_meta.confidence is None:
        soft.append("missing_confidence")
    if entry.resolution_meta.source_trust is None:
        soft.append("missing_source_trust")

    if reasons:
        return ProvenanceGateResult(
            passed=False,
            reason_codes=tuple(reasons + soft),
            forced_state=ResolutionState.UNKNOWN,
            explanation=(
                "Required provenance/metadata missing; "
                "entry is not admissible as load-bearing context."
            ),
        )

    return ProvenanceGateResult(
        passed=True,
        reason_codes=tuple(soft),
        forced_state=None,
        explanation="Provenance gate passed.",
    )


__all__ = [
    "ProvenanceGateResult",
    "evaluate_provenance_gate",
]
