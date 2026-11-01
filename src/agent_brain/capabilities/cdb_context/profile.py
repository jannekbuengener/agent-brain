"""CDB-specific profile for the ``cdb_context`` capability.

This module is intentionally product-specific and must NOT be imported by
generic Agent Brain core packages (``core``, ``context``, ``retrieval``,
``evidence``, ``memory``, ``connectors``). It only supplies profile data and
policy pointers; Claire runtime code is never imported.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_brain.context import RequiredReadRule, RequiredReadsProfile
from agent_brain.core.source_priority import SourcePriority

# Repository identity — GitHub/Repo live remain authoritative.
CDB_REPOSITORY_OWNER = "jannekbuengener"
CDB_REPOSITORY_NAME = "Claire_de_Binare"
CDB_REPOSITORY_IDENTITY = f"{CDB_REPOSITORY_OWNER}/{CDB_REPOSITORY_NAME}"
CDB_GITHUB_TREE_BASE = f"https://github.com/{CDB_REPOSITORY_IDENTITY}/blob/HEAD"

# Source priority for CDB work (injected; not hard-coded into generic ranking).
CDB_SOURCE_PRIORITY = SourcePriority(
    ordered_sources=(
        "github_live",
        "repo_live",
        "verified_agent_brain_context",
        "persisted_index",
    )
)

# Guardrails — context only; no execution / live-capital authority.
CDB_GUARDRAILS: tuple[str, ...] = (
    "Agent Brain provides context and evidence only; GitHub and repo live state remain authoritative",
    "cdb_context does not authorize execution, capital deployment, or risk controls",
    "persistierte Context darf Live-State niemals still überschreiben",
    "keine Secrets, Broker-Credentials oder lokalen Secret-Pfade materialisieren",
)


def _source_ref(path: str) -> str:
    return f"github:{CDB_REPOSITORY_IDENTITY}:{path}"


def build_cdb_required_reads_profile() -> RequiredReadsProfile:
    """CDB Required-Read policy pointing at canonical Claire sources.

    Not a static full copy of the Claire canon — only resolvable policy rules.
    Irrelevant tasks must not artificially load the entire catalog.
    """
    minimum = (
        RequiredReadRule(
            path="AGENTS.md",
            priority="critical",
            reason="Claire root agent pointer and session compass",
            source_ref=_source_ref("AGENTS.md"),
        ),
        RequiredReadRule(
            path="docs/meta/REPOSITORY_CANON.md",
            priority="critical",
            reason="Claire repository canon / authority baseline",
            source_ref=_source_ref("docs/meta/REPOSITORY_CANON.md"),
        ),
        RequiredReadRule(
            path="CURRENT_STATUS.md",
            priority="high",
            reason="Live engineering status pointer for Claire",
            source_ref=_source_ref("CURRENT_STATUS.md"),
        ),
        RequiredReadRule(
            path="knowledge/governance/CDB_CONSTITUTION.md",
            priority="high",
            reason="Constitutional / authority boundary context (not execution authority)",
            source_ref=_source_ref("knowledge/governance/CDB_CONSTITUTION.md"),
        ),
    )
    conditional = (
        RequiredReadRule(
            path="knowledge/governance/CDB_GOVERNANCE.md",
            priority="high",
            reason="Governance context when task touches governance/policy",
            source_ref=_source_ref("knowledge/governance/CDB_GOVERNANCE.md"),
            keywords=("governance", "policy", "constitution", "authority"),
        ),
        RequiredReadRule(
            path="knowledge/governance/CDB_AGENT_POLICY.md",
            priority="high",
            reason="Agent policy when task touches agent behaviour",
            source_ref=_source_ref("knowledge/governance/CDB_AGENT_POLICY.md"),
            keywords=("agent policy", "agenten", "workforce", "roles"),
        ),
        RequiredReadRule(
            path="knowledge/CDB_KNOWLEDGE_HUB.md",
            priority="medium",
            reason="Knowledge hub when task needs knowledge/navigation",
            source_ref=_source_ref("knowledge/CDB_KNOWLEDGE_HUB.md"),
            keywords=("knowledge", "hub", "navigation", "docs"),
        ),
        RequiredReadRule(
            path="knowledge/testing/README.md",
            priority="high",
            reason="Test-first contract when task is about tests",
            source_ref=_source_ref("knowledge/testing/README.md"),
            keywords=("test", "pytest", "tdd", "fixture"),
        ),
        RequiredReadRule(
            path="docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md",
            priority="medium",
            reason="Agent surface matrix for onboarding / host surface work",
            source_ref=_source_ref("docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md"),
            keywords=("onboarding", "surface", "plugin", "host", "adapter"),
        ),
        RequiredReadRule(
            path="docs/runbooks/CONTROL_REGISTER.md",
            priority="high",
            reason="Control register as context for operational stage questions",
            source_ref=_source_ref("docs/runbooks/CONTROL_REGISTER.md"),
            keywords=("control register", "stage", "operations", "runbook"),
        ),
        RequiredReadRule(
            path="docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
            priority="high",
            reason="Live-readiness audit status as context only (no go authority)",
            source_ref=_source_ref("docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"),
            keywords=("live readiness", "readiness", "lr-audit", "audit status"),
        ),
        RequiredReadRule(
            path="docs/db",
            priority="medium",
            reason="Database docs when task touches Surreal / storage",
            source_ref=_source_ref("docs/db"),
            keywords=("surreal", "database", "storage", "db"),
        ),
        RequiredReadRule(
            path="README.md",
            priority="medium",
            reason="Repository README for orientation tasks",
            source_ref=_source_ref("README.md"),
            keywords=("readme", "overview", "orientation", "getting started"),
        ),
    )
    return RequiredReadsProfile(minimum=minimum, conditional=conditional)


@dataclass(frozen=True, slots=True)
class CdbContextProfile:
    """Bounded CDB profile consumed by the capability surface."""

    repository_identity: str = CDB_REPOSITORY_IDENTITY
    github_tree_base: str = CDB_GITHUB_TREE_BASE
    source_priority: SourcePriority = CDB_SOURCE_PRIORITY
    guardrails: tuple[str, ...] = CDB_GUARDRAILS
    required_reads_profile: RequiredReadsProfile | None = None
    source_classes: tuple[str, ...] = (
        "repository_docs",
        "governance",
        "status",
        "runbooks",
        "knowledge",
    )

    def __post_init__(self) -> None:
        if self.required_reads_profile is None:
            object.__setattr__(
                self,
                "required_reads_profile",
                build_cdb_required_reads_profile(),
            )

    def to_dict(self) -> dict[str, object]:
        assert self.required_reads_profile is not None
        return {
            "repository_identity": self.repository_identity,
            "github_tree_base": self.github_tree_base,
            "source_priority": {"ordered_sources": list(self.source_priority.ordered_sources)},
            "guardrails": list(self.guardrails),
            "source_classes": list(self.source_classes),
            "required_reads_minimum_count": len(self.required_reads_profile.minimum),
            "required_reads_conditional_count": len(self.required_reads_profile.conditional),
        }


def default_cdb_context_profile() -> CdbContextProfile:
    return CdbContextProfile()


__all__ = [
    "CDB_GITHUB_TREE_BASE",
    "CDB_GUARDRAILS",
    "CDB_REPOSITORY_IDENTITY",
    "CDB_REPOSITORY_NAME",
    "CDB_REPOSITORY_OWNER",
    "CDB_SOURCE_PRIORITY",
    "CdbContextProfile",
    "build_cdb_required_reads_profile",
    "default_cdb_context_profile",
]
