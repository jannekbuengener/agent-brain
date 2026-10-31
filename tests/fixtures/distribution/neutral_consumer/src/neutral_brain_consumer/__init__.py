"""Minimal neutral consumer used to prove Agent Brain pinning (#17).

Product-neutral fixture only: no host-app business logic.
"""

from __future__ import annotations

from importlib import metadata

from agent_brain.distribution import (
    evaluate_consumer_expectations,
    snapshot_public_surface,
    verify_installed_version,
)

CONSUMER_EXPECTED_EXPORTS: dict[str, tuple[str, ...]] = {
    "agent_brain": ("__version__",),
    "agent_brain.distribution": (
        "PinSpec",
        "UpgradePlan",
        "RollbackPlan",
        "snapshot_public_surface",
        "evaluate_consumer_expectations",
        "verify_installed_version",
    ),
    "agent_brain.contracts": ("EvidenceRef", "ClaimRef", "require_compatible_version"),
    "agent_brain.core": ("canonical_hash", "SourcePriority"),
    "agent_brain.memory": ("MemoryStore", "MemoryScope", "MemoryReadService"),
}


def expected_agent_brain_version() -> str:
    return metadata.version("agent-brain")


def smoke(pinned_version: str) -> dict[str, object]:
    """Load Agent Brain from the installed pin and verify the consumer contract."""
    installed = verify_installed_version(pinned_version)
    surface = snapshot_public_surface()
    compatibility = evaluate_consumer_expectations(
        expected_exports=CONSUMER_EXPECTED_EXPORTS,
        actual_exports=surface.exports,
    )
    if not compatibility.is_compatible:
        missing = ", ".join(sorted(compatibility.missing_expected))
        raise RuntimeError(f"consumer contract incompatible: missing {missing}")
    return {
        "pinned_version": pinned_version,
        "installed_version": installed,
        "compatible": True,
        "public_modules": sorted(surface.exports),
    }


__all__ = [
    "CONSUMER_EXPECTED_EXPORTS",
    "expected_agent_brain_version",
    "smoke",
]
