from importlib import import_module
from pathlib import Path

import pytest


def test_stable_identity_and_provenance_are_product_neutral() -> None:
    identity = import_module("agent_brain.core.identity")

    stable = identity.StableIdentity(namespace="run", value="abc-123")
    provenance = identity.ProvenanceStamp(
        source="repository",
        reference="path/to/source",
        content_hash="deadbeef",
    )

    assert stable.namespace == "run"
    assert stable.value == "abc-123"
    assert provenance.source == "repository"
    assert provenance.reference == "path/to/source"
    assert provenance.content_hash == "deadbeef"


def test_identity_and_provenance_reject_blank_required_fields() -> None:
    identity = import_module("agent_brain.core.identity")

    with pytest.raises(ValueError):
        identity.StableIdentity(namespace=" ", value="abc")
    with pytest.raises(ValueError):
        identity.ProvenanceStamp(source="repository", reference=" ")


def test_source_priority_uses_only_injected_order() -> None:
    priority_module = import_module("agent_brain.core.source_priority")
    priority = priority_module.SourcePriority(("live", "repo", "fallback"))

    assert priority.rank("live") == 0
    assert priority.rank("repo") == 1
    assert priority.rank("unknown") is None
    assert priority.prefers("live", "repo") is True
    assert priority.prefers("fallback", "repo") is False


def test_source_priority_rejects_duplicates_and_blank_names() -> None:
    priority_module = import_module("agent_brain.core.source_priority")

    with pytest.raises(ValueError):
        priority_module.SourcePriority(("repo", "repo"))
    with pytest.raises(ValueError):
        priority_module.SourcePriority(("repo", " "))


def test_policy_hook_is_injectable_without_product_policy() -> None:
    policy = import_module("agent_brain.core.policy")

    class ReadOnlyPolicy:
        def evaluate(self, context):
            if context.operation == "read":
                return policy.PolicyDecision(allowed=True)
            return policy.PolicyDecision(allowed=False, reasons=("read-only profile",))

    hook: policy.PolicyHook = ReadOnlyPolicy()

    assert hook.evaluate(policy.PolicyContext(operation="read")).allowed is True
    blocked = hook.evaluate(policy.PolicyContext(operation="write"))
    assert blocked.allowed is False
    assert blocked.reasons == ("read-only profile",)


def test_foundation_source_contains_no_claire_specific_vocabulary(repo_root: Path) -> None:
    core_root = repo_root / "src" / "agent_brain" / "core"
    forbidden = ("claire", "cdb_", "echtgeld", "live-go", "trading")
    violations: list[str] = []

    for path in core_root.glob("*.py"):
        content = path.read_text(encoding="utf-8").lower()
        for term in forbidden:
            if term in content:
                violations.append(f"{path.name}:{term}")

    assert not violations, "Product-specific vocabulary leaked into foundation: " + ", ".join(
        violations
    )
