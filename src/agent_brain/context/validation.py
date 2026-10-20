"""Product-neutral validation planning for Agent Brain briefings."""

from __future__ import annotations

from dataclasses import dataclass

from agent_brain.core.canonical import canonical_hash

VALIDATION_PLAN_SCHEMA = "validation-plan/v1"
_LEVELS = frozenset({"low", "medium", "high"})


class ValidationPlanError(ValueError):
    """Raised when a validation-plan input violates the portable contract."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValidationPlanError(f"{field_name} must not be blank")
    return normalized


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(item, field_name) for item in values)


def _level(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name).lower()
    if normalized not in _LEVELS:
        raise ValidationPlanError(f"{field_name} must be one of: low, medium, high")
    return normalized


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


@dataclass(frozen=True, slots=True)
class ValidationPlanInput:
    impact_id: str
    impact_level: str = "low"
    confidence: str = "low"
    required_checks: tuple[str, ...] = ()
    suggested_tests: tuple[str, ...] = ()
    docs_to_review: tuple[str, ...] = ()
    evidence_to_collect: tuple[str, ...] = ()
    commands_to_consider: tuple[str, ...] = ()
    blocking_preconditions: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    manual_review_needed: bool = False


@dataclass(frozen=True, slots=True)
class ValidationPlan:
    schema_version: str
    plan_id: str
    impact_id: str
    impact_level: str
    confidence: str
    required_checks: tuple[str, ...]
    suggested_tests: tuple[str, ...]
    docs_to_review: tuple[str, ...]
    evidence_to_collect: tuple[str, ...]
    commands_to_consider: tuple[str, ...]
    blocking_preconditions: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    manual_review_needed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "impact_id": self.impact_id,
            "impact_level": self.impact_level,
            "confidence": self.confidence,
            "required_checks": list(self.required_checks),
            "suggested_tests": list(self.suggested_tests),
            "docs_to_review": list(self.docs_to_review),
            "evidence_to_collect": list(self.evidence_to_collect),
            "commands_to_consider": list(self.commands_to_consider),
            "blocking_preconditions": list(self.blocking_preconditions),
            "stop_conditions": list(self.stop_conditions),
            "manual_review_needed": self.manual_review_needed,
        }


def build_validation_plan(input: ValidationPlanInput) -> ValidationPlan:
    """Build a deterministic plan without deriving product-specific authority."""
    if not isinstance(input, ValidationPlanInput):
        raise TypeError("input must be a ValidationPlanInput")
    if not isinstance(input.manual_review_needed, bool):
        raise TypeError("manual_review_needed must be a bool")

    impact_id = _required_text(input.impact_id, "impact_id")
    impact_level = _level(input.impact_level, "impact_level")
    confidence = _level(input.confidence, "confidence")
    required_checks = _text_tuple(input.required_checks, "required_checks")
    suggested_tests = _text_tuple(input.suggested_tests, "suggested_tests")
    docs_to_review = _text_tuple(input.docs_to_review, "docs_to_review")
    evidence_to_collect = _text_tuple(input.evidence_to_collect, "evidence_to_collect")
    commands_to_consider = _text_tuple(input.commands_to_consider, "commands_to_consider")
    blocking_preconditions = _text_tuple(
        input.blocking_preconditions,
        "blocking_preconditions",
    )
    stop_conditions = _text_tuple(input.stop_conditions, "stop_conditions")

    if input.manual_review_needed:
        blocking_preconditions = _dedupe((*blocking_preconditions, "manual_review_required"))
        stop_conditions = _dedupe((*stop_conditions, "manual_review_required"))

    stable_payload = {
        "schema_version": VALIDATION_PLAN_SCHEMA,
        "impact_id": impact_id,
        "impact_level": impact_level,
        "confidence": confidence,
        "required_checks": list(required_checks),
        "suggested_tests": list(suggested_tests),
        "docs_to_review": list(docs_to_review),
        "evidence_to_collect": list(evidence_to_collect),
        "commands_to_consider": list(commands_to_consider),
        "blocking_preconditions": list(blocking_preconditions),
        "stop_conditions": list(stop_conditions),
        "manual_review_needed": input.manual_review_needed,
    }
    plan_id = f"validation_{canonical_hash(stable_payload)[:24]}"

    return ValidationPlan(
        schema_version=VALIDATION_PLAN_SCHEMA,
        plan_id=plan_id,
        impact_id=impact_id,
        impact_level=impact_level,
        confidence=confidence,
        required_checks=required_checks,
        suggested_tests=suggested_tests,
        docs_to_review=docs_to_review,
        evidence_to_collect=evidence_to_collect,
        commands_to_consider=commands_to_consider,
        blocking_preconditions=blocking_preconditions,
        stop_conditions=stop_conditions,
        manual_review_needed=input.manual_review_needed,
    )
