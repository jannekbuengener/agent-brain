"""SurrealDB integration boundary (#10 / #21 / #38).

Provides fail-closed read settings and adapters without requiring a SurrealDB
SDK dependency. Live Docker/datastore starts remain an ops concern outside
this package.
"""

from agent_brain.surrealdb.config import SurrealDbReadSettings
from agent_brain.surrealdb.delivery import (
    SurrealReadHandoffBundle,
    build_read_handoff_bundle,
    settings_from_runtime_truth,
)
from agent_brain.surrealdb.handoff import (
    ClassDisposition,
    HandoffOutcome,
    StateDisposition,
    StateHandoffDecision,
    VolumeAuthority,
    decide_state_handoff,
    issue_38_scratch_handoff_decision_2026_10_31,
)
from agent_brain.surrealdb.knowledge_store import SurrealKnowledgeStore
from agent_brain.surrealdb.memory_store import SurrealMemoryStore
from agent_brain.surrealdb.runtime_truth import (
    SurrealRuntimeTruth,
    evidence_backed_handoff_2026_10_31,
    local_runtime_truth_2026_10_31,
)
from agent_brain.surrealdb.state_classification import (
    CANONICAL_STATE_CLASSES,
    StateClassFinding,
    StateClassStatus,
    classify_canonical_classes_from_table_map,
    classify_table_presence,
    issue_38_scratch_findings_2026_10_31,
)
from agent_brain.surrealdb.statement_guard import (
    WriteDeniedError,
    classify_readonly_statement,
)

__all__ = [
    "CANONICAL_STATE_CLASSES",
    "ClassDisposition",
    "HandoffOutcome",
    "StateClassFinding",
    "StateClassStatus",
    "StateDisposition",
    "StateHandoffDecision",
    "SurrealDbReadSettings",
    "SurrealKnowledgeStore",
    "SurrealMemoryStore",
    "SurrealReadHandoffBundle",
    "SurrealRuntimeTruth",
    "VolumeAuthority",
    "WriteDeniedError",
    "build_read_handoff_bundle",
    "classify_canonical_classes_from_table_map",
    "classify_readonly_statement",
    "classify_table_presence",
    "decide_state_handoff",
    "evidence_backed_handoff_2026_10_31",
    "issue_38_scratch_findings_2026_10_31",
    "issue_38_scratch_handoff_decision_2026_10_31",
    "local_runtime_truth_2026_10_31",
    "settings_from_runtime_truth",
]
