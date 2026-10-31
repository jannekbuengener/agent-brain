"""Retrieval-Stop-Auflösung (Slice 7, Task 5).

Löst einen Retrieval-Stop über einen injizierten ``PolicyHook`` auf und
übersetzt das ``PolicyDecision`` in den bestehenden ``RetrievalStop``-
Contract (Task 1). Fail-conservative: Policy-Ausnahmen führen zu einem
konservativen STOP. Keine Trading-/Live-/Execution-Autorität, keine
#8-/ #10-Semantik.
"""

from __future__ import annotations

from collections.abc import Mapping

from agent_brain.core.policy import PolicyContext, PolicyDecision, PolicyHook
from agent_brain.retrieval.contract import RETRIEVAL_STOP_SCHEMA, RetrievalStop


def _default_stop_reason(decision: PolicyDecision) -> str:
    if decision.reasons:
        return "; ".join(decision.reasons)
    return "policy_denied"


def resolve_retrieval_stop(
    *,
    policy_hook: PolicyHook,
    operation: str,
    context_attributes: Mapping[str, object] | None = None,
) -> RetrievalStop:
    """Löst einen Retrieval-Stop über einen PolicyHook auf.

    - ``allowed=True`` → kein STOP (``RetrievalStop(allowed=True)``).
    - ``allowed=False`` → konservativer STOP mit Grund aus der Decision.
    - Policy-Ausnahme oder ungültige Decision → fail-conservativer STOP.
    """
    context_attributes = context_attributes or {}

    context = PolicyContext(
        operation=operation,
        attributes=context_attributes,
    )

    try:
        decision = policy_hook.evaluate(context)
    except Exception as exc:  # noqa: BLE001 - policy hooks may raise arbitrary errors
        return RetrievalStop(
            schema_version=RETRIEVAL_STOP_SCHEMA,
            stop_id=f"stop_{operation}",
            reason=f"policy_evaluation_failed: {exc}",
            allowed=False,
            decision_refs=(),
        )

    if not isinstance(decision, PolicyDecision):
        return RetrievalStop(
            schema_version=RETRIEVAL_STOP_SCHEMA,
            stop_id=f"stop_{operation}",
            reason="invalid_policy_decision",
            allowed=False,
            decision_refs=(),
        )

    if decision.allowed:
        return RetrievalStop(
            schema_version=RETRIEVAL_STOP_SCHEMA,
            stop_id=f"stop_{operation}",
            reason="policy_allowed",
            allowed=True,
            decision_refs=(),
        )

    return RetrievalStop(
        schema_version=RETRIEVAL_STOP_SCHEMA,
        stop_id=f"stop_{operation}",
        reason=_default_stop_reason(decision),
        allowed=False,
        decision_refs=(),
    )
