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
    board_manager_actor,
    github_issue_work_ref,
)
from agent_brain.improvement.memory import InMemoryImprovementObservationStore
from agent_brain.improvement.ports import (
    ImprovementObservationStore,
    SubmitObservationResult,
)
<<<<<<< Updated upstream
from agent_brain.improvement.protocol import (
    ImprovementCapability,
    ImprovementProtocolGateway,
    ProtocolCaller,
    ProtocolDenied,
    capability_readback,
    tool_schemas,
=======
from agent_brain.improvement.projection import (
    PROJECTION_VERSION,
    ImprovementMarkdownProjection,
    ProjectionExportResult,
    compute_source_hash,
>>>>>>> Stashed changes
)
from agent_brain.improvement.sqlite import SqliteImprovementObservationStore

__all__ = [
    "DedupeAssessment",
    "DedupeSignal",
    "ImprovementCapability",
    "ImprovementIdentityAmbiguous",
    "ImprovementManagementPort",
    "ImprovementMarkdownProjection",
    "ImprovementObservationStore",
<<<<<<< Updated upstream
    "ImprovementProtocolGateway",
=======
    "ImprovementProjectionConflict",
>>>>>>> Stashed changes
    "ImprovementStoreError",
    "ImprovementStoreUnavailable",
    "ImprovementValidationError",
    "InMemoryImprovementManagementPort",
    "InMemoryImprovementObservationStore",
    "InvalidImprovementScope",
    "ManagementActor",
<<<<<<< Updated upstream
    "ProtocolCaller",
    "ProtocolDenied",
=======
    "PROJECTION_VERSION",
    "ProjectionExportResult",
>>>>>>> Stashed changes
    "SqliteImprovementObservationStore",
    "SubmitObservationResult",
    "assess_observation",
    "board_manager_actor",
<<<<<<< Updated upstream
    "capability_readback",
=======
    "compute_source_hash",
>>>>>>> Stashed changes
    "github_issue_work_ref",
    "merge_improvements",
    "relate_improvements",
    "tool_schemas",
]
