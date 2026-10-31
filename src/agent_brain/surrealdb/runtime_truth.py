"""Shared Surreal runtime truth for #10 / #21 / #38 / #67.

This module freezes the verified local inventory facts so read adapters and
handoff decisions consume the same evidence. It does not start Docker or open
datastores.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_brain.surrealdb.handoff import (
    StateHandoffDecision,
    VolumeAuthority,
    decide_state_handoff,
)
from agent_brain.surrealdb.state_classification import (
    StateClassFinding,
    issue_38_scratch_findings_2026_10_31,
)


@dataclass(frozen=True, slots=True)
class SurrealRuntimeTruth:
    """One coherent snapshot of verified Surreal facts for Agent Brain."""

    evidence_ref: str
    server_version: str
    image_digest: str
    original_volume: str
    scratch_volume: str
    storage_engine: str
    versioning_enabled: bool
    configured_namespace: str
    configured_database: str
    configured_namespace_present: bool
    only_local_surrealkv_claire_volume: bool
    alternate_surreal_volumes_checked: tuple[str, ...]
    host_claire_surreal_dirs_present: bool
    root_namespaces: tuple[str, ...]
    volume_authority: VolumeAuthority
    state_class_findings: tuple[StateClassFinding, ...]

    def handoff_decision(self) -> StateHandoffDecision:
        return decide_state_handoff(
            self.state_class_findings,
            volume_authority=self.volume_authority,
            evidence_ref=self.evidence_ref,
        )


def local_runtime_truth_2026_10_31() -> SurrealRuntimeTruth:
    """Evidence-backed local truth after Docker scratch inventory + ELSEWHERE search.

    Volume authority is ``confirmed_primary`` because:
    - Compose maps Claire local SurrealKV exclusively to ``cdb_database_surrealdb_data``
    - No other SurrealKV Claire/context volume exists on this Docker engine
    - ``claude-memory`` is not SurrealKV (JS blob only)
    - No Claire host data dirs with SurrealKV were found
    - Configured ``cdb_context_local`` is ABSENT on that volume (never created)
    """
    return SurrealRuntimeTruth(
        evidence_ref="docs/surrealdb/RUNTIME_BASELINE_2026-10-31.md",
        server_version="3.0.4",
        image_digest=(
            "sha256:65000ff205b08363b035b457f292dc0a0b1cd4212935dd5ea94073cf67adf306"
        ),
        original_volume="cdb_database_surrealdb_data",
        scratch_volume="agent_brain_38_surrealdb_scratch_20261031",
        storage_engine="surrealkv",
        versioning_enabled=False,
        configured_namespace="cdb_context_local",
        configured_database="cdb_context_intel",
        configured_namespace_present=False,
        only_local_surrealkv_claire_volume=True,
        alternate_surreal_volumes_checked=(
            "cdb_database_surrealdb_data",
            "agent_brain_38_surrealdb_scratch_20261031",
            "claude-memory",
        ),
        host_claire_surreal_dirs_present=False,
        root_namespaces=("main", "governance"),
        volume_authority=VolumeAuthority.CONFIRMED_PRIMARY,
        state_class_findings=issue_38_scratch_findings_2026_10_31(),
    )


def evidence_backed_handoff_2026_10_31() -> StateHandoffDecision:
    """Handoff decision from shared runtime truth after ELSEWHERE search."""
    return local_runtime_truth_2026_10_31().handoff_decision()
