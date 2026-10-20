"""Side-effect-free context self-explanation contracts and builder."""

from __future__ import annotations

from dataclasses import dataclass

from agent_brain.contracts.evidence import ClaimRef, EvidenceRef
from agent_brain.core.canonical import canonical_hash

SELF_EXPLANATION_SCHEMA = "self-explanation/v1"
_SUPPORTED_TYPES = frozenset(
    {
        "why_blocked",
        "why_risky",
        "why_stale",
        "why_decision_current",
        "why_decision_superseded",
        "why_scope_blocked",
        "why_evidence_weak",
        "why_agent_needs_go",
        "why_doc_untrusted",
    }
)
_DEFAULT_GUARDRAIL = "explanation_does_not_authorize_action"


class SelfExplanationError(ValueError):
    """Raised when an explanation input violates the portable contract."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise SelfExplanationError(f"{field_name} must not be blank")
    return normalized


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(values: object, field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    result = tuple(_required_text(item, field_name) for item in values)
    if not allow_empty and not result:
        raise SelfExplanationError(f"{field_name} must not be empty")
    return result


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


@dataclass(frozen=True, slots=True)
class SelfExplanationInput:
    explanation_type: str
    summary: str
    reasons: tuple[str, ...]
    evidence_refs: tuple[EvidenceRef, ...]
    required_next_step: str
    confidence: float | None = None
    scope_context: str | None = None
    graph_path: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    claim_refs: tuple[ClaimRef, ...] = ()
    related_refs: tuple[str, ...] = ()
    recommended_next_reads: tuple[str, ...] = ()
    guardrails: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SelfExplanation:
    schema_version: str
    explanation_id: str
    explanation_type: str
    summary: str
    reasons: tuple[str, ...]
    evidence_refs: tuple[EvidenceRef, ...]
    required_next_step: str
    confidence: float | None
    scope_context: str | None
    graph_path: tuple[str, ...]
    uncertainties: tuple[str, ...]
    claim_refs: tuple[ClaimRef, ...]
    related_refs: tuple[str, ...]
    recommended_next_reads: tuple[str, ...]
    guardrails: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "explanation_id": self.explanation_id,
            "explanation_type": self.explanation_type,
            "summary": self.summary,
            "reasons": list(self.reasons),
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
            "required_next_step": self.required_next_step,
            "graph_path": list(self.graph_path),
            "uncertainties": list(self.uncertainties),
            "claim_refs": [item.to_dict() for item in self.claim_refs],
            "related_refs": list(self.related_refs),
            "recommended_next_reads": list(self.recommended_next_reads),
            "guardrails": list(self.guardrails),
        }
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.scope_context is not None:
            payload["scope_context"] = self.scope_context
        return payload


def supported_explanation_types() -> frozenset[str]:
    """Return the supported portable explanation kinds."""
    return _SUPPORTED_TYPES


def build_self_explanation(input: SelfExplanationInput) -> SelfExplanation:
    """Build deterministic explanation evidence without granting action authority."""
    if not isinstance(input, SelfExplanationInput):
        raise TypeError("input must be a SelfExplanationInput")

    explanation_type = _required_text(input.explanation_type, "explanation_type")
    if explanation_type not in _SUPPORTED_TYPES:
        raise SelfExplanationError(f"unsupported explanation_type: {explanation_type!r}")
    summary = _required_text(input.summary, "summary")
    reasons = _text_tuple(input.reasons, "reasons", allow_empty=False)
    required_next_step = _required_text(input.required_next_step, "required_next_step")
    scope_context = _optional_text(input.scope_context, "scope_context")
    graph_path = _text_tuple(input.graph_path, "graph_path")
    uncertainties = list(_text_tuple(input.uncertainties, "uncertainties"))
    related_refs = _text_tuple(input.related_refs, "related_refs")
    recommended_next_reads = _text_tuple(
        input.recommended_next_reads,
        "recommended_next_reads",
    )
    guardrails = _text_tuple(input.guardrails, "guardrails")

    if not isinstance(input.evidence_refs, (tuple, list)) or not input.evidence_refs:
        raise SelfExplanationError("evidence_refs must not be empty")
    for item in input.evidence_refs:
        if not isinstance(item, EvidenceRef):
            raise TypeError("evidence_refs entries must be EvidenceRef values")
    evidence_refs = tuple(input.evidence_refs)

    if not isinstance(input.claim_refs, (tuple, list)):
        raise TypeError("claim_refs must be a tuple or list of ClaimRef values")
    for item in input.claim_refs:
        if not isinstance(item, ClaimRef):
            raise TypeError("claim_refs entries must be ClaimRef values")
    claim_refs = tuple(input.claim_refs)

    confidence: float | None
    if input.confidence is None:
        confidence = None
    else:
        if isinstance(input.confidence, bool) or not isinstance(input.confidence, (int, float)):
            raise TypeError("confidence must be a number")
        confidence = float(input.confidence)
        if not 0.0 <= confidence <= 1.0:
            raise SelfExplanationError("confidence must be between 0.0 and 1.0")
        if confidence < 0.5:
            uncertainties.append("low_confidence")
    if explanation_type == "why_evidence_weak":
        uncertainties.append("weak_evidence")

    normalized_uncertainties = _dedupe(tuple(uncertainties))
    normalized_guardrails = _dedupe((_DEFAULT_GUARDRAIL, *guardrails))

    stable_payload = {
        "schema_version": SELF_EXPLANATION_SCHEMA,
        "explanation_type": explanation_type,
        "summary": summary,
        "reasons": list(reasons),
        "evidence_refs": [item.to_dict() for item in evidence_refs],
        "required_next_step": required_next_step,
        "confidence": confidence,
        "scope_context": scope_context,
        "graph_path": list(graph_path),
        "uncertainties": list(normalized_uncertainties),
        "claim_refs": [item.to_dict() for item in claim_refs],
        "related_refs": list(related_refs),
        "recommended_next_reads": list(recommended_next_reads),
        "guardrails": list(normalized_guardrails),
    }
    explanation_id = f"explain_{canonical_hash(stable_payload)[:24]}"

    return SelfExplanation(
        schema_version=SELF_EXPLANATION_SCHEMA,
        explanation_id=explanation_id,
        explanation_type=explanation_type,
        summary=summary,
        reasons=reasons,
        evidence_refs=evidence_refs,
        required_next_step=required_next_step,
        confidence=confidence,
        scope_context=scope_context,
        graph_path=graph_path,
        uncertainties=normalized_uncertainties,
        claim_refs=claim_refs,
        related_refs=related_refs,
        recommended_next_reads=recommended_next_reads,
        guardrails=normalized_guardrails,
    )
