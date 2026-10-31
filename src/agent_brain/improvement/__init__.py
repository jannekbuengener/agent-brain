"""Typed Skill Improvement Blackboard domain (separate from Memory/Knowledge)."""

from agent_brain.improvement.dedupe import (
    DedupeAssessment,
    DedupeSignal,
    assess_observation,
    merge_improvements,
    relate_improvements,
)
from agent_brain.improvement.errors import (
    ImprovementIdentityAmbiguous,
    ImprovementStoreError,
    ImprovementStoreUnavailable,
    ImprovementValidationError,
    InvalidImprovementScope,
)
from agent_brain.improvement.management import (
    ImprovementManagementPort,
    InMemoryImprovementManagementPort,
    ManagementActor,
    board_manager_actor,
    github_issue_work_ref,
)
from agent_brain.improvement.memory import InMemoryImprovementObservationStore
from agent_brain.improvement.ports import (
    ImprovementObservationStore,
    SubmitObservationResult,
)
from agent_brain.improvement.sqlite import SqliteImprovementObservationStore

__all__ = [
    "DedupeAssessment",
    "DedupeSignal",
    "ImprovementIdentityAmbiguous",
    "ImprovementManagementPort",
    "ImprovementObservationStore",
    "ImprovementStoreError",
    "ImprovementStoreUnavailable",
    "ImprovementValidationError",
    "InMemoryImprovementManagementPort",
    "InMemoryImprovementObservationStore",
    "InvalidImprovementScope",
    "ManagementActor",
    "SqliteImprovementObservationStore",
    "SubmitObservationResult",
    "assess_observation",
    "board_manager_actor",
    "github_issue_work_ref",
    "merge_improvements",
    "relate_improvements",
]
