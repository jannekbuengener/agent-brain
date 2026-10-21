"""Stop Resolver Tests (Slice 7, Task 5).

RED-first: Diese Tests definieren das erwartete Verhalten der
fail-conservativen Retrieval-Stop-Auflösung über PolicyHook/PolicyDecision
und müssen vor der Implementierung fehlschlagen.
"""

from __future__ import annotations

from agent_brain.core.policy import PolicyContext, PolicyDecision, PolicyHook
from agent_brain.retrieval.contract import RetrievalStop
from agent_brain.retrieval.stop_resolver import resolve_retrieval_stop


class AllowingHook(PolicyHook):
    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        return PolicyDecision(allowed=True, reasons=())


class DenyingHook(PolicyHook):
    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        return PolicyDecision(allowed=False, reasons=("policy_denied",))


class ExceptionHook(PolicyHook):
    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        raise RuntimeError("policy evaluation failed")


def test_allowed_true_yields_no_stop() -> None:
    hook = AllowingHook()
    stop = resolve_retrieval_stop(
        policy_hook=hook,
        operation="retrieval.read",
        context_attributes={},
    )
    assert isinstance(stop, RetrievalStop)
    assert stop.allowed is True
    assert stop.reason == "policy_allowed"
    assert stop.decision_refs == ()


def test_allowed_false_yields_conservative_stop() -> None:
    hook = DenyingHook()
    stop = resolve_retrieval_stop(
        policy_hook=hook,
        operation="retrieval.read",
        context_attributes={},
    )
    assert stop.allowed is False
    assert stop.reason == "policy_denied"
    assert stop.decision_refs == ()


def test_empty_reason_is_preserved() -> None:
    class EmptyReasonHook(PolicyHook):
        def evaluate(self, context: PolicyContext) -> PolicyDecision:
            return PolicyDecision(allowed=False, reasons=())

    hook = EmptyReasonHook()
    stop = resolve_retrieval_stop(
        policy_hook=hook,
        operation="retrieval.read",
        context_attributes={},
    )
    assert stop.allowed is False
    assert stop.reason == "policy_denied"


def test_policy_exception_is_fail_closed_stop() -> None:
    hook = ExceptionHook()
    stop = resolve_retrieval_stop(
        policy_hook=hook,
        operation="retrieval.read",
        context_attributes={},
    )
    assert stop.allowed is False
    assert stop.reason != ""
    assert "policy evaluation failed" in stop.reason or "stop" in stop.reason.lower()


def test_deterministic_reason_for_denied_decision() -> None:
    hook = DenyingHook()
    first = resolve_retrieval_stop(
        policy_hook=hook,
        operation="retrieval.read",
        context_attributes={},
    )
    second = resolve_retrieval_stop(
        policy_hook=hook,
        operation="retrieval.read",
        context_attributes={},
    )
    assert first == second


def test_repeated_evaluation_identical() -> None:
    hook = DenyingHook()
    results = tuple(
        resolve_retrieval_stop(
            policy_hook=hook,
            operation="retrieval.read",
            context_attributes={"key": "value"},
        )
        for _ in range(3)
    )
    assert all(result == results[0] for result in results)


def test_no_wall_clock_in_stop_resolution() -> None:
    hook = DenyingHook()
    first = resolve_retrieval_stop(
        policy_hook=hook,
        operation="retrieval.read",
        context_attributes={},
    )
    second = resolve_retrieval_stop(
        policy_hook=hook,
        operation="retrieval.read",
        context_attributes={},
    )
    assert first == second


def test_no_runtime_or_host_dependency() -> None:
    import inspect

    import agent_brain.retrieval.stop_resolver as mod

    module_path = mod.__file__ or ""
    assert "claire" not in module_path.lower()
    assert "trading" not in module_path.lower()
    assert "surrealdb" not in module_path.lower()

    source = inspect.getsource(mod)
    assert "/home/" not in source
    assert "C:" not in source


def test_no_decision_trust_claim_semantics() -> None:
    import agent_brain.retrieval.stop_resolver as mod

    source = mod.__file__ or ""
    assert "trust" not in source.lower()
    assert "claim" not in source.lower()
    assert "contradiction" not in source.lower()
    assert "stale" not in source.lower()
    assert "scope_drift" not in source.lower()


def test_no_db_or_network_usage() -> None:
    import agent_brain.retrieval.stop_resolver as mod

    source = mod.__file__ or ""
    assert "surreal" not in source.lower()
    assert "http" not in source.lower()
    assert "socket" not in source.lower()


def test_retrieval_stop_roundtrip() -> None:
    stop = RetrievalStop(
        schema_version="retrieval-stop/v1",
        stop_id="stop-1",
        reason="policy_denied",
        allowed=False,
        decision_refs=(),
    )
    parsed = RetrievalStop.from_dict(stop.to_dict())
    assert parsed == stop
