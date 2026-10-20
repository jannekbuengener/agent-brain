"""Portable Agent Briefing request/result contracts and pure builder."""

from __future__ import annotations

from dataclasses import dataclass

from agent_brain.context.package import ContextPackage
from agent_brain.context.required_reads import RequiredRead
from agent_brain.context.validation import ValidationPlan
from agent_brain.contracts.evidence import EvidenceRef
from agent_brain.core.canonical import canonical_hash
from agent_brain.core.policy import PolicyContext, PolicyHook

BRIEFING_SCHEMA = "agent-briefing/v1"
_DEPTHS = frozenset({"quick", "standard", "deep"})
_RISK_LEVELS = frozenset({"low", "medium", "high"})
_DEFAULT_GUARDRAIL = "briefing_does_not_authorize_action"


class BriefingError(ValueError):
    """Raised when a briefing request violates the portable contract."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise BriefingError(f"{field_name} must not be blank")
    return normalized


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(item, field_name) for item in values)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


@dataclass(frozen=True, slots=True)
class BriefingRequest:
    task_id: str
    task_scope: str
    target_issue: str | None
    requested_depth: str
    operation_mode: str
    target_paths: tuple[str, ...] = ()
    target_symbols: tuple[str, ...] = ()
    target_concepts: tuple[str, ...] = ()
    risk_level: str = "medium"

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "task_scope": self.task_scope,
            "target_issue": self.target_issue,
            "requested_depth": self.requested_depth,
            "operation_mode": self.operation_mode,
            "target_paths": list(self.target_paths),
            "target_symbols": list(self.target_symbols),
            "target_concepts": list(self.target_concepts),
            "risk_level": self.risk_level,
        }


@dataclass(frozen=True, slots=True)
class BriefingEnvelope:
    schema_version: str
    briefing_id: str
    scope_summary: str
    context_package_ref: str | None
    required_reads: tuple[RequiredRead, ...]
    relevant_evidence: tuple[EvidenceRef, ...]
    validation_plan: ValidationPlan | None
    guardrails: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    human_go_required: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "briefing_id": self.briefing_id,
            "scope_summary": self.scope_summary,
            "context_package_ref": self.context_package_ref,
            "required_reads": [item.to_dict() for item in self.required_reads],
            "relevant_evidence": [item.to_dict() for item in self.relevant_evidence],
            "validation_plan": self.validation_plan.to_dict() if self.validation_plan else None,
            "guardrails": list(self.guardrails),
            "stop_conditions": list(self.stop_conditions),
            "unresolved_questions": list(self.unresolved_questions),
            "human_go_required": self.human_go_required,
        }


def _normalize_request(request: BriefingRequest) -> BriefingRequest:
    if not isinstance(request, BriefingRequest):
        raise TypeError("request must be a BriefingRequest")
    task_id = _required_text(request.task_id, "task_id")
    task_scope = _required_text(request.task_scope, "task_scope")
    target_issue = _optional_text(request.target_issue, "target_issue")
    if not isinstance(request.requested_depth, str) or request.requested_depth not in _DEPTHS:
        raise BriefingError("requested_depth must be one of: quick, standard, deep")
    operation_mode = _required_text(request.operation_mode, "operation_mode")
    target_paths = _text_tuple(request.target_paths, "target_paths")
    target_symbols = _text_tuple(request.target_symbols, "target_symbols")
    target_concepts = _text_tuple(request.target_concepts, "target_concepts")
    if not isinstance(request.risk_level, str) or request.risk_level not in _RISK_LEVELS:
        raise BriefingError("risk_level must be one of: low, medium, high")
    return BriefingRequest(
        task_id=task_id,
        task_scope=task_scope,
        target_issue=target_issue,
        requested_depth=request.requested_depth,
        operation_mode=operation_mode,
        target_paths=target_paths,
        target_symbols=target_symbols,
        target_concepts=target_concepts,
        risk_level=request.risk_level,
    )


def build_briefing(
    request: BriefingRequest,
    *,
    context_package: ContextPackage | None,
    required_reads: tuple[RequiredRead, ...] = (),
    evidence_refs: tuple[EvidenceRef, ...] = (),
    validation_plan: ValidationPlan | None = None,
    guardrails: tuple[str, ...] = (),
    stop_conditions: tuple[str, ...] = (),
    unresolved_questions: tuple[str, ...] = (),
    policy_hook: PolicyHook | None = None,
) -> BriefingEnvelope:
    """Build a deterministic task briefing without granting execution authority."""
    normalized = _normalize_request(request)

    if context_package is not None and not isinstance(context_package, ContextPackage):
        raise TypeError("context_package must be a ContextPackage when present")
    for item in required_reads:
        if not isinstance(item, RequiredRead):
            raise TypeError("required_reads entries must be RequiredRead values")
    for item in evidence_refs:
        if not isinstance(item, EvidenceRef):
            raise TypeError("evidence_refs entries must be EvidenceRef values")
    if validation_plan is not None and not isinstance(validation_plan, ValidationPlan):
        raise TypeError("validation_plan must be a ValidationPlan when present")

    normalized_guardrails = _dedupe((_DEFAULT_GUARDRAIL, *_text_tuple(guardrails, "guardrails")))
    normalized_stops = list(_text_tuple(stop_conditions, "stop_conditions"))
    normalized_questions = _text_tuple(unresolved_questions, "unresolved_questions")
    human_go_required = False

    if validation_plan is not None:
        normalized_stops.extend(validation_plan.stop_conditions)
        if validation_plan.manual_review_needed:
            human_go_required = True

    if policy_hook is not None:
        decision = policy_hook.evaluate(
            PolicyContext(
                operation="build_briefing",
                attributes={
                    "task_id": normalized.task_id,
                    "task_scope": normalized.task_scope,
                    "target_issue": normalized.target_issue,
                    "requested_depth": normalized.requested_depth,
                    "operation_mode": normalized.operation_mode,
                    "risk_level": normalized.risk_level,
                },
            )
        )
        if not isinstance(decision.allowed, bool):
            raise TypeError("policy decision allowed must be a bool")
        reasons = _text_tuple(decision.reasons, "policy reasons")
        if not decision.allowed:
            human_go_required = True
            normalized_stops.extend(reasons or ("policy_denied",))

    stops = _dedupe(tuple(normalized_stops))
    reads = tuple(required_reads)
    evidence = tuple(evidence_refs)
    scope_summary = (
        f"{normalized.task_scope} "
        f"[depth={normalized.requested_depth}; risk={normalized.risk_level}; "
        f"mode={normalized.operation_mode}]"
    )
    context_package_ref = context_package.package_id if context_package is not None else None

    stable_payload = {
        "schema_version": BRIEFING_SCHEMA,
        "request": normalized.to_dict(),
        "scope_summary": scope_summary,
        "context_package_ref": context_package_ref,
        "required_reads": [item.to_dict() for item in reads],
        "relevant_evidence": [item.to_dict() for item in evidence],
        "validation_plan": validation_plan.to_dict() if validation_plan else None,
        "guardrails": list(normalized_guardrails),
        "stop_conditions": list(stops),
        "unresolved_questions": list(normalized_questions),
        "human_go_required": human_go_required,
    }
    briefing_id = f"briefing_{canonical_hash(stable_payload)[:24]}"

    return BriefingEnvelope(
        schema_version=BRIEFING_SCHEMA,
        briefing_id=briefing_id,
        scope_summary=scope_summary,
        context_package_ref=context_package_ref,
        required_reads=reads,
        relevant_evidence=evidence,
        validation_plan=validation_plan,
        guardrails=normalized_guardrails,
        stop_conditions=stops,
        unresolved_questions=normalized_questions,
        human_go_required=human_go_required,
    )
