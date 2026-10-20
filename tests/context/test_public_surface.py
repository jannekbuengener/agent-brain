from __future__ import annotations

from agent_brain import context

PUBLIC_NAMES = {
    "BRIEFING_SCHEMA",
    "CONTEXT_PACKAGE_SCHEMA",
    "SELF_EXPLANATION_SCHEMA",
    "VALIDATION_PLAN_SCHEMA",
    "BriefingEnvelope",
    "BriefingError",
    "BriefingRequest",
    "ContextArtifact",
    "ContextPackage",
    "ContextPackageError",
    "ContextPackageRequest",
    "RedactionRecord",
    "RequiredRead",
    "RequiredReadRule",
    "RequiredReadsProfile",
    "SelfExplanation",
    "SelfExplanationError",
    "SelfExplanationInput",
    "ValidationPlan",
    "ValidationPlanError",
    "ValidationPlanInput",
    "build_briefing",
    "build_context_package",
    "build_self_explanation",
    "build_validation_plan",
    "resolve_required_reads",
    "supported_explanation_types",
}


def test_context_package_exports_slice_4_public_surface() -> None:
    assert PUBLIC_NAMES <= set(context.__all__)
    for name in PUBLIC_NAMES:
        assert hasattr(context, name)
