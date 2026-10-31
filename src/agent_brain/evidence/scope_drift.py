"""Scope drift detection and blocking output."""

from __future__ import annotations

import fnmatch
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from agent_brain.core.canonical import canonical_hash
from agent_brain.evidence.contract import (
    SCOPE_DRIFT_BLOCKING_SCHEMA,
    SCOPE_DRIFT_FINDING_SCHEMA,
    SCOPE_DRIFT_REPORT_SCHEMA,
    ArtifactState,
    ScopeDriftBlocking,
    ScopeDriftError,
    ScopeDriftFinding,
    ScopeDriftPolicy,
    ScopeDriftReport,
    SurfaceState,
)

_DEFAULT_LIMITATIONS = (
    "Scope drift findings are informational; presence of authorization refs is not authorization.",
)


@dataclass(frozen=True, slots=True)
class ScopeDriftBundle:
    artifacts: tuple[ArtifactState, ...] = ()
    declared_paths: tuple[str, ...] = ()
    observed_paths: tuple[str, ...] = ()
    declared_domains: tuple[str, ...] = ()
    observed_domains: tuple[str, ...] = ()
    declared_issues: tuple[str, ...] = ()
    observed_issues: tuple[str, ...] = ()
    surfaces: tuple[SurfaceState, ...] = ()
    operation_modes: tuple[str, ...] = ()
    authorization_refs: tuple[str, ...] = ()
    write_intent: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.artifacts, tuple):
            raise ScopeDriftError("artifacts must be a tuple")


def _drift_id(drift_type: str, subject: str) -> str:
    return canonical_hash({"drift_type": drift_type, "subject": subject})[:16]


def _path_in_scope(path: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        if path == pattern or path.startswith(f"{pattern}/"):
            return True
    return False


def detect_scope_drift(
    *,
    bundle: ScopeDriftBundle,
    policy: ScopeDriftPolicy,
    as_of: datetime,
) -> ScopeDriftReport:
    if not isinstance(bundle, ScopeDriftBundle):
        raise ScopeDriftError("bundle must be a ScopeDriftBundle")
    if policy is None:
        raise ScopeDriftError("policy is required")
    if not isinstance(as_of, datetime):
        raise ScopeDriftError("as_of must be a datetime")

    findings: list[ScopeDriftFinding] = []
    if policy.target_paths:
        for path in bundle.observed_paths:
            if not _path_in_scope(path, policy.target_paths):
                findings.append(
                    ScopeDriftFinding(
                        schema_version=SCOPE_DRIFT_FINDING_SCHEMA,
                        finding_id=_drift_id("path_out_of_scope", path),
                        drift_type="path_out_of_scope",
                        severity="warning",
                        status="open",
                        detected_at=as_of,
                        explanation=f"Observed path {path} is outside declared target paths.",
                    )
                )

    for surface in bundle.surfaces:
        if surface.surface_id in policy.forbidden_surfaces:
            findings.append(
                ScopeDriftFinding(
                    schema_version=SCOPE_DRIFT_FINDING_SCHEMA,
                    finding_id=_drift_id("forbidden_surface_touched", surface.surface_id),
                    drift_type="forbidden_surface_touched",
                    severity="blocking",
                    status="open",
                    detected_at=as_of,
                    explanation=f"Forbidden surface touched: {surface.surface_id}",
                )
            )
        if surface.surface_type in policy.protected_surface_types:
            findings.append(
                ScopeDriftFinding(
                    schema_version=SCOPE_DRIFT_FINDING_SCHEMA,
                    finding_id=_drift_id("runtime_surface_touched", surface.surface_id),
                    drift_type="runtime_surface_touched",
                    severity="warning",
                    status="open",
                    detected_at=as_of,
                    explanation=f"Protected runtime surface touched: {surface.surface_id}",
                )
            )

    if policy.allowed_domains:
        for domain in bundle.observed_domains:
            if domain not in policy.allowed_domains:
                findings.append(
                    ScopeDriftFinding(
                        schema_version=SCOPE_DRIFT_FINDING_SCHEMA,
                        finding_id=_drift_id("domain_out_of_scope", domain),
                        drift_type="domain_out_of_scope",
                        severity="warning",
                        status="open",
                        detected_at=as_of,
                        explanation=f"Domain {domain} is outside allowed domains.",
                    )
                )

    if policy.allowed_issues:
        for issue in bundle.observed_issues:
            if issue not in policy.allowed_issues:
                findings.append(
                    ScopeDriftFinding(
                        schema_version=SCOPE_DRIFT_FINDING_SCHEMA,
                        finding_id=_drift_id("issue_out_of_scope", issue),
                        drift_type="issue_out_of_scope",
                        severity="warning",
                        status="open",
                        detected_at=as_of,
                        explanation=f"Issue {issue} is outside allowed issues.",
                    )
                )

    if policy.target_paths and len(bundle.artifacts) > policy.max_artifact_count:
        findings.append(
            ScopeDriftFinding(
                schema_version=SCOPE_DRIFT_FINDING_SCHEMA,
                finding_id=_drift_id("unexpected_dependency_expansion", "artifacts"),
                drift_type="unexpected_dependency_expansion",
                severity="warning",
                status="open",
                detected_at=as_of,
                explanation="Artifact count exceeds configured maximum.",
            )
        )

    if bundle.write_intent and not bundle.authorization_refs:
        findings.append(
            ScopeDriftFinding(
                schema_version=SCOPE_DRIFT_FINDING_SCHEMA,
                finding_id=_drift_id("write_intent_without_authorization_ref", "write_intent"),
                drift_type="write_intent_without_authorization_ref",
                severity="blocking",
                status="open",
                detected_at=as_of,
                explanation="Write intent declared without authorization reference.",
            )
        )

    for mode in bundle.operation_modes:
        if mode in policy.write_like_operation_modes and not bundle.authorization_refs:
            findings.append(
                ScopeDriftFinding(
                    schema_version=SCOPE_DRIFT_FINDING_SCHEMA,
                    finding_id=_drift_id("write_mode_without_authorization_ref", mode),
                    drift_type="write_mode_without_authorization_ref",
                    severity="blocking",
                    status="open",
                    detected_at=as_of,
                    explanation=f"Write-like operation mode {mode} without authorization reference.",
                )
            )

    findings.sort(key=lambda item: (item.drift_type, item.finding_id))
    blocking_count = sum(1 for item in findings if item.severity == "blocking")
    return ScopeDriftReport(
        schema_version=SCOPE_DRIFT_REPORT_SCHEMA,
        findings=tuple(findings),
        blocking_count=blocking_count,
        warnings=(),
        limitations=_DEFAULT_LIMITATIONS,
    )


def build_scope_drift_blocking(report: ScopeDriftReport) -> ScopeDriftBlocking:
    blocking_findings = tuple(item for item in report.findings if item.severity == "blocking")
    return ScopeDriftBlocking(
        schema_version=SCOPE_DRIFT_BLOCKING_SCHEMA,
        blocking=bool(blocking_findings),
        blocking_count=len(blocking_findings),
        summary="Scope drift blocking summary.",
        affected_artifact_refs=(),
        findings=blocking_findings,
        recommended_actions=("review",),
        recommended_next_reads=(),
    )
