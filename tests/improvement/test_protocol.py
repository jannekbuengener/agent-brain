from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    IMPROVEMENT_WORK_REF_SCHEMA,
    ImprovementLifecycle,
    ImprovementObservation,
    ImprovementPriority,
    ImprovementWorkRef,
    WorkRefKind,
)
from agent_brain.improvement.cli import main as cli_main
from agent_brain.improvement.protocol import (
    ImprovementCapability,
    ImprovementProtocolGateway,
    ProtocolCaller,
    ProtocolDenied,
    capability_readback,
    tool_schemas,
)


def _obs(observation_id: str, key: str) -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id=observation_id,
        agent_id="agent-a",
        run_id="run-1",
        skill_id="cursor-meta-epic-executor",
        observation="mid-layout capture",
        recommendation="stable geometry gate",
        evidence=(f"e-{observation_id}",),
        timestamp=datetime(2026, 10, 31, 18, 0, tzinfo=UTC),
        idempotency_key=key,
        root_cause_key="host-visual-evidence-floor",
        repository_ref="jannekbuengener/agent-workforce",
    )


def test_tool_schemas_are_versioned_and_host_neutral() -> None:
    schemas = tool_schemas()
    assert schemas["schema_version"] == "improvement-protocol/v1"
    tools = schemas["tools"]
    assert "submit_improvement_observation" in tools
    assert tools["set_improvement_priority"]["capability"] == "improvement_management_write"
    assert "mcp" not in str(schemas).lower()


def test_capability_readback_separates_read_observation_management() -> None:
    caller = ProtocolCaller(
        actor_id="writer-1",
        run_id="run-1",
        capabilities=frozenset(
            {
                ImprovementCapability.READ,
                ImprovementCapability.OBSERVATION_WRITE,
            }
        ),
    )
    readback = capability_readback(caller)
    assert readback["capabilities"] == {
        "READ": True,
        "OBSERVATION_WRITE": True,
        "MANAGEMENT_WRITE": False,
    }


def test_observation_submit_idempotent_via_protocol() -> None:
    gateway = ImprovementProtocolGateway()
    caller = ProtocolCaller(
        actor_id="writer-1",
        run_id="run-1",
        capabilities=frozenset(
            {
                ImprovementCapability.READ,
                ImprovementCapability.OBSERVATION_WRITE,
            }
        ),
    )
    first = gateway.invoke(
        caller,
        "submit_improvement_observation",
        observation=_obs("obs-1", "idem-1"),
    )
    retry = gateway.invoke(
        caller,
        "submit_improvement_observation",
        observation=_obs("obs-1", "idem-1"),
    )
    assert first.created_new_observation is True
    assert retry.created_new_observation is False
    listed = gateway.invoke(caller, "list_improvements", skill_id="cursor-meta-epic-executor")
    assert len(listed) == 1


def test_management_denied_without_capability() -> None:
    gateway = ImprovementProtocolGateway()
    writer = ProtocolCaller(
        actor_id="writer-1",
        run_id="run-1",
        capabilities=frozenset({ImprovementCapability.OBSERVATION_WRITE}),
    )
    gateway.invoke(
        writer,
        "submit_improvement_observation",
        observation=_obs("obs-1", "idem-1"),
    )
    improvement_id = gateway.store.list_improvements()[0].improvement_id
    with pytest.raises(ProtocolDenied, match="improvement_management_write"):
        gateway.invoke(
            writer,
            "set_improvement_priority",
            improvement_id=improvement_id,
            priority=ImprovementPriority.HIGH,
            reason="nope",
        )


def test_management_allowed_with_explicit_capability() -> None:
    gateway = ImprovementProtocolGateway()
    writer = ProtocolCaller(
        actor_id="writer-1",
        run_id="run-1",
        capabilities=frozenset({ImprovementCapability.OBSERVATION_WRITE}),
    )
    gateway.invoke(
        writer,
        "submit_improvement_observation",
        observation=_obs("obs-1", "k1"),
    )
    gateway.invoke(
        writer,
        "submit_improvement_observation",
        observation=_obs("obs-2", "k2"),
    )
    manager = ProtocolCaller(
        actor_id="board-1",
        run_id="run-mgmt",
        capabilities=frozenset(
            {
                ImprovementCapability.READ,
                ImprovementCapability.MANAGEMENT_WRITE,
            }
        ),
    )
    improvement_id = gateway.store.list_improvements()[0].improvement_id
    validated = gateway.invoke(
        manager,
        "transition_improvement_lifecycle",
        improvement_id=improvement_id,
        target=ImprovementLifecycle.VALIDATED,
        reason="board validated",
    )
    assert validated.lifecycle is ImprovementLifecycle.VALIDATED
    linked = gateway.invoke(
        manager,
        "link_work_item",
        improvement_id=improvement_id,
        work_ref=ImprovementWorkRef(
            schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
            kind=WorkRefKind.GITHUB_ISSUE,
            repository_ref="jannekbuengener/agent-workforce",
            ref="123",
        ),
    )
    assert any(ref.ref == "123" for ref in linked.work_refs)


def test_cli_capabilities_and_denied_invoke(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        cli_main(
            [
                "capabilities",
                "--actor",
                "a",
                "--run",
                "r",
                "--cap",
                "improvement_read",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert '"READ":true' in out.replace(" ", "") or '"READ": true' in out
    assert (
        cli_main(
            [
                "invoke",
                "--actor",
                "a",
                "--run",
                "r",
                "--cap",
                "improvement_read",
                "--tool",
                "set_improvement_priority",
                "--payload",
                '{"improvement_id":"x","priority":"HIGH","reason":"no"}',
            ]
        )
        == 2
    )
    err = capsys.readouterr().err
    assert "ProtocolDenied" in err
