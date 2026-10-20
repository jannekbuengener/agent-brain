"""Portable Context Package and Briefing Core."""

from agent_brain.context.briefing import (
    BRIEFING_SCHEMA,
    BriefingEnvelope,
    BriefingError,
    BriefingRequest,
    build_briefing,
)
from agent_brain.context.explanation import (
    SELF_EXPLANATION_SCHEMA,
    SelfExplanation,
    SelfExplanationError,
    SelfExplanationInput,
    build_self_explanation,
    supported_explanation_types,
)
from agent_brain.context.package import (
    CONTEXT_PACKAGE_SCHEMA,
    ContextArtifact,
    ContextPackage,
    ContextPackageError,
    ContextPackageRequest,
    RedactionRecord,
    build_context_package,
)
from agent_brain.context.required_reads import (
    RequiredRead,
    RequiredReadRule,
    RequiredReadsProfile,
    resolve_required_reads,
)
from agent_brain.context.validation import (
    VALIDATION_PLAN_SCHEMA,
    ValidationPlan,
    ValidationPlanError,
    ValidationPlanInput,
    build_validation_plan,
)

__all__ = [
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
]
