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
    ImprovementProjectionConflict,
    ImprovementStoreError,
    ImprovementStoreUnavailable,
    ImprovementValidationError,
    InvalidImprovementScope,
)
from agent_brain.improvement.management import (
    ImprovementManagementPort,
    InMemoryImprovementManagementPort,
    ManagementActor,
    SurrealImprovementManagementPort,
    board_manager_actor,
    github_issue_work_ref,
)
from agent_brain.improvement.memory import InMemoryImprovementObservationStore
from agent_brain.improvement.ports import (
    ImprovementObservationStore,
    SubmitObservationResult,
)
from agent_brain.improvement.projection import (
    PROJECTION_VERSION,
    ImprovementMarkdownProjection,
    ProjectionExportResult,
    compute_source_hash,
)
from agent_brain.improvement.protocol import (
    ImprovementCapability,
    ImprovementProtocolGateway,
    ProtocolCaller,
    ProtocolDenied,
    capability_readback,
    tool_schemas,
)
from agent_brain.improvement.sqlite import SqliteImprovementObservationStore
from agent_brain.improvement.surreal import SurrealImprovementObservationStore

__all__ = [
    "PROJECTION_VERSION",
    "DedupeAssessment",
    "DedupeSignal",
    "ImprovementCapability",
    "ImprovementIdentityAmbiguous",
    "ImprovementManagementPort",
    "ImprovementMarkdownProjection",
    "ImprovementObservationStore",
    "ImprovementProjectionConflict",
    "ImprovementProtocolGateway",
    "ImprovementStoreError",
    "ImprovementStoreUnavailable",
    "ImprovementValidationError",
    "InMemoryImprovementManagementPort",
    "InMemoryImprovementObservationStore",
    "InvalidImprovementScope",
    "ManagementActor",
    "ProjectionExportResult",
    "ProtocolCaller",
    "ProtocolDenied",
    "SqliteImprovementObservationStore",
    "SubmitObservationResult",
    "SurrealImprovementManagementPort",
    "SurrealImprovementObservationStore",
    "assess_observation",
    "board_manager_actor",
    "capability_readback",
    "compute_source_hash",
    "github_issue_work_ref",
    "merge_improvements",
    "relate_improvements",
    "tool_schemas",
]
