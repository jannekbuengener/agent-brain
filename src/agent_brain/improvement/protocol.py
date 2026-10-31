"""Capability-gated Improvement protocol surface (#50).

Separate from Slice #12 read-only extraction surface. No MCP runtime dependency;
tool schemas are host-neutral JSON descriptors for adapters to bind.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    IMPROVEMENT_WORK_REF_SCHEMA,
    Improvement,
    ImprovementLifecycle,
    ImprovementObservation,
    ImprovementPriority,
    ImprovementWorkRef,
    WorkRefKind,
)
from agent_brain.improvement.errors import ImprovementValidationError, InvalidImprovementScope
from agent_brain.improvement.management import (
    InMemoryImprovementManagementPort,
    ManagementActor,
    board_manager_actor,
)
from agent_brain.improvement.memory import InMemoryImprovementObservationStore
from agent_brain.improvement.ports import SubmitObservationResult

PROTOCOL_SCHEMA_VERSION = "improvement-protocol/v1"


class ImprovementCapability(StrEnum):
    """Capability IDs aligned with Agent Workforce registry semantics."""

    READ = "improvement_read"
    OBSERVATION_WRITE = "improvement_observation_write"
    MANAGEMENT_WRITE = "improvement_management_write"


class ProtocolDenied(InvalidImprovementScope):
    """Caller lacks the required capability for the requested tool."""


@dataclass(frozen=True, slots=True)
class ProtocolCaller:
    """Audit-bound caller identity + granted capabilities."""

    actor_id: str
    run_id: str
    capabilities: frozenset[ImprovementCapability]

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise ValueError("actor_id must not be blank")
        if not self.run_id.strip():
            raise ValueError("run_id must not be blank")
        object.__setattr__(self, "capabilities", frozenset(self.capabilities))

    def allow(self, capability: ImprovementCapability) -> bool:
        return capability in self.capabilities


OBSERVATION_TOOLS = frozenset(
    {
        "submit_improvement_observation",
        "get_improvement",
        "list_improvements",
        "find_improvement_candidates",
    }
)
MANAGEMENT_TOOLS = frozenset(
    {
        "merge_improvements",
        "set_improvement_priority",
        "transition_improvement_lifecycle",
        "link_work_item",
        "record_verification",
    }
)


def tool_schemas() -> dict[str, dict[str, object]]:
    """Host-neutral, versioned tool descriptors (no MCP dependency)."""
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "tools": {
            "submit_improvement_observation": {
                "capability": ImprovementCapability.OBSERVATION_WRITE.value,
                "input": {"observation": "improvement-observation/v1"},
                "output": "SubmitObservationResult",
            },
            "get_improvement": {
                "capability": ImprovementCapability.READ.value,
                "input": {"improvement_id": "string"},
                "output": "Improvement | null",
            },
            "list_improvements": {
                "capability": ImprovementCapability.READ.value,
                "input": {
                    "skill_id": "string?",
                    "repository_ref": "string?",
                    "lifecycle": "ImprovementLifecycle?",
                },
                "output": "Improvement[]",
            },
            "find_improvement_candidates": {
                "capability": ImprovementCapability.READ.value,
                "input": {
                    "skill_id": "string",
                    "root_cause_key": "string?",
                    "repository_ref": "string?",
                },
                "output": "Improvement[]",
            },
            "set_improvement_priority": {
                "capability": ImprovementCapability.MANAGEMENT_WRITE.value,
                "input": {
                    "improvement_id": "string",
                    "priority": "ImprovementPriority",
                    "reason": "string",
                    "expected_revision": "int?",
                },
                "output": "Improvement",
            },
            "transition_improvement_lifecycle": {
                "capability": ImprovementCapability.MANAGEMENT_WRITE.value,
                "input": {
                    "improvement_id": "string",
                    "target": "ImprovementLifecycle",
                    "reason": "string",
                    "expected_revision": "int?",
                },
                "output": "Improvement",
            },
            "merge_improvements": {
                "capability": ImprovementCapability.MANAGEMENT_WRITE.value,
                "input": {
                    "target_improvement_id": "string",
                    "source_improvement_ids": "string[]",
                    "reason": "string",
                    "evidence": "string[]",
                    "merge_id": "string",
                    "merged_at": "datetime",
                },
                "output": "Improvement",
            },
            "link_work_item": {
                "capability": ImprovementCapability.MANAGEMENT_WRITE.value,
                "input": {"improvement_id": "string", "work_ref": "improvement-work-ref/v1"},
                "output": "Improvement",
            },
            "record_verification": {
                "capability": ImprovementCapability.MANAGEMENT_WRITE.value,
                "input": {"improvement_id": "string", "work_ref": "improvement-work-ref/v1"},
                "output": "Improvement",
            },
        },
    }


def capability_readback(caller: ProtocolCaller) -> dict[str, object]:
    """Explicit READ / OBSERVATION_WRITE / MANAGEMENT_WRITE visibility."""
    granted = {item.value for item in caller.capabilities}
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "actor_id": caller.actor_id,
        "run_id": caller.run_id,
        "capabilities": {
            "READ": ImprovementCapability.READ.value in granted,
            "OBSERVATION_WRITE": ImprovementCapability.OBSERVATION_WRITE.value in granted,
            "MANAGEMENT_WRITE": ImprovementCapability.MANAGEMENT_WRITE.value in granted,
        },
        "granted": sorted(granted),
        "observation_tools": sorted(OBSERVATION_TOOLS),
        "management_tools": sorted(MANAGEMENT_TOOLS),
    }


class ImprovementProtocolGateway:
    """Default-deny management; observation/read require explicit capabilities."""

    def __init__(
        self,
        observation_store: InMemoryImprovementObservationStore | None = None,
        management_port: InMemoryImprovementManagementPort | None = None,
    ) -> None:
        self._store = observation_store or InMemoryImprovementObservationStore()
        self._management = management_port or InMemoryImprovementManagementPort(self._store)

    @property
    def store(self) -> InMemoryImprovementObservationStore:
        return self._store

    def invoke(self, caller: ProtocolCaller, tool: str, **payload: Any) -> object:
        if tool in {"get_improvement", "list_improvements", "find_improvement_candidates"}:
            self._require(caller, ImprovementCapability.READ, tool)
        elif tool == "submit_improvement_observation":
            self._require(caller, ImprovementCapability.OBSERVATION_WRITE, tool)
        elif tool in MANAGEMENT_TOOLS:
            self._require(caller, ImprovementCapability.MANAGEMENT_WRITE, tool)
        else:
            raise ImprovementValidationError(f"unknown improvement protocol tool: {tool}")

        if tool == "submit_improvement_observation":
            observation = payload.get("observation")
            if isinstance(observation, dict):
                observation = ImprovementObservation.from_dict(observation)
            if not isinstance(observation, ImprovementObservation):
                raise TypeError("observation must be ImprovementObservation or mapping")
            return self._store.submit_observation(observation)

        if tool == "get_improvement":
            return self._store.get_improvement(str(payload["improvement_id"]))

        if tool == "list_improvements":
            return self._store.list_improvements(
                skill_id=payload.get("skill_id"),
                repository_ref=payload.get("repository_ref"),
                lifecycle=payload.get("lifecycle"),
            )

        if tool == "find_improvement_candidates":
            return self._store.find_candidates(
                skill_id=str(payload["skill_id"]),
                root_cause_key=payload.get("root_cause_key"),
                repository_ref=payload.get("repository_ref"),
            )

        actor = self._management_actor(caller)
        if tool == "set_improvement_priority":
            return self._management.set_priority(
                str(payload["improvement_id"]),
                payload["priority"],
                actor=actor,
                reason=str(payload["reason"]),
                expected_revision=payload.get("expected_revision"),
            )
        if tool == "transition_improvement_lifecycle":
            return self._management.transition_lifecycle(
                str(payload["improvement_id"]),
                payload["target"],
                actor=actor,
                reason=str(payload["reason"]),
                expected_revision=payload.get("expected_revision"),
            )
        if tool == "merge_improvements":
            merged_at = payload["merged_at"]
            if isinstance(merged_at, str):
                merged_at = datetime.fromisoformat(merged_at.replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
            return self._management.merge_improvements(
                str(payload["target_improvement_id"]),
                payload["source_improvement_ids"],
                actor=actor,
                reason=str(payload["reason"]),
                evidence=payload.get("evidence", ()),
                merge_id=str(payload["merge_id"]),
                merged_at=merged_at,
            )
        if tool == "link_work_item":
            work_ref = self._work_ref(payload["work_ref"], WorkRefKind.GITHUB_ISSUE)
            return self._management.link_work_item(
                str(payload["improvement_id"]),
                work_ref,
                actor=actor,
                expected_revision=payload.get("expected_revision"),
            )
        if tool == "record_verification":
            work_ref = self._work_ref(payload["work_ref"], WorkRefKind.VERIFICATION)
            return self._management.record_verification(
                str(payload["improvement_id"]),
                work_ref,
                actor=actor,
                expected_revision=payload.get("expected_revision"),
            )
        raise ImprovementValidationError(f"unhandled tool: {tool}")

    def _require(
        self,
        caller: ProtocolCaller,
        capability: ImprovementCapability,
        tool: str,
    ) -> None:
        if not caller.allow(capability):
            raise ProtocolDenied(
                f"denied tool {tool!r}: missing capability {capability.value} "
                f"for actor={caller.actor_id} run={caller.run_id}"
            )

    def _management_actor(self, caller: ProtocolCaller) -> ManagementActor:
        return board_manager_actor(caller.actor_id)

    def _work_ref(self, raw: object, expected_kind: WorkRefKind) -> ImprovementWorkRef:
        if isinstance(raw, ImprovementWorkRef):
            work_ref = raw
        elif isinstance(raw, dict):
            work_ref = ImprovementWorkRef.from_dict(raw)
        else:
            raise TypeError("work_ref must be ImprovementWorkRef or mapping")
        if work_ref.kind is not expected_kind:
            raise ImprovementValidationError(
                f"work_ref.kind must be {expected_kind.value}, got {work_ref.kind.value}"
            )
        return work_ref


def result_to_dict(value: object) -> object:
    """Serialize protocol results for CLI/JSON adapters."""
    if value is None:
        return None
    if isinstance(value, SubmitObservationResult):
        return {
            "observation": value.observation.to_dict(),
            "improvement": value.improvement.to_dict(),
            "created_new_observation": value.created_new_observation,
            "created_new_improvement": value.created_new_improvement,
        }
    if isinstance(value, Improvement):
        return value.to_dict()
    if isinstance(value, tuple):
        return [result_to_dict(item) for item in value]
    if isinstance(value, (str, int, float, bool, dict, list)):
        return value
    raise TypeError(f"unsupported protocol result type: {type(value)!r}")


# Re-export schema constants for adapters without importing contracts directly.
__all__ = [
    "IMPROVEMENT_OBSERVATION_SCHEMA",
    "IMPROVEMENT_WORK_REF_SCHEMA",
    "ImprovementCapability",
    "ImprovementLifecycle",
    "ImprovementPriority",
    "ImprovementProtocolGateway",
    "PROTOCOL_SCHEMA_VERSION",
    "ProtocolCaller",
    "ProtocolDenied",
    "capability_readback",
    "result_to_dict",
    "tool_schemas",
]
