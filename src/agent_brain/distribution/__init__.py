"""Distribution, versioning, and consumer-contract surface (#17).

This package is the stable, product-neutral contract that external consumers
use to pin, verify, upgrade, and roll back Agent Brain. It contains no
Claire-specific business logic and does not implement CLI/protocol (#12) or
Claire cutover (#13).
"""

from __future__ import annotations

from agent_brain.distribution.compatibility import (
    ChangeKind,
    CompatibilityReport,
    CompatibilityVerdict,
    classify_surface_diff,
    evaluate_consumer_expectations,
)
from agent_brain.distribution.lifecycle import (
    LifecycleStep,
    RollbackPlan,
    UpgradePlan,
    build_rollback_plan,
    build_upgrade_plan,
)
from agent_brain.distribution.pinning import (
    DISTRIBUTION_MODEL,
    FORBIDDEN_PIN_REFS,
    PinKind,
    PinSpec,
    format_requirement,
    parse_pin_spec,
    reject_moving_ref,
    verify_installed_version,
)
from agent_brain.distribution.surface import (
    PUBLIC_PACKAGE_MODULES,
    PublicSurfaceSnapshot,
    compare_public_surfaces,
    snapshot_public_surface,
)
from agent_brain.distribution.version import (
    PACKAGE_NAME,
    PackageVersion,
    declared_version_from_pyproject,
    get_package_version,
    parse_package_version,
    version_git_tag,
)

__all__ = [
    "DISTRIBUTION_MODEL",
    "FORBIDDEN_PIN_REFS",
    "PACKAGE_NAME",
    "PUBLIC_PACKAGE_MODULES",
    "ChangeKind",
    "CompatibilityReport",
    "CompatibilityVerdict",
    "LifecycleStep",
    "PackageVersion",
    "PinKind",
    "PinSpec",
    "PublicSurfaceSnapshot",
    "RollbackPlan",
    "UpgradePlan",
    "build_rollback_plan",
    "build_upgrade_plan",
    "classify_surface_diff",
    "compare_public_surfaces",
    "declared_version_from_pyproject",
    "evaluate_consumer_expectations",
    "format_requirement",
    "get_package_version",
    "parse_package_version",
    "parse_pin_spec",
    "reject_moving_ref",
    "snapshot_public_surface",
    "verify_installed_version",
    "version_git_tag",
]
