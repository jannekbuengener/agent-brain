"""Documented, testable upgrade and rollback procedures for consumers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from agent_brain.distribution.compatibility import CompatibilityReport
from agent_brain.distribution.pinning import PinKind, PinSpec, format_requirement
from agent_brain.distribution.version import parse_package_version


@dataclass(frozen=True, slots=True)
class LifecycleStep:
    """One ordered step in an upgrade or rollback procedure."""

    name: str
    description: str
    requirement: str | None = None


@dataclass(frozen=True, slots=True)
class UpgradePlan:
    current_version: str
    target_version: str
    current_pin: PinSpec
    target_pin: PinSpec
    steps: tuple[LifecycleStep, ...]
    compatibility: CompatibilityReport | None = None

    @property
    def target_requirement(self) -> str:
        return format_requirement(self.target_pin)


@dataclass(frozen=True, slots=True)
class RollbackPlan:
    failed_version: str
    previous_version: str
    previous_pin: PinSpec
    steps: tuple[LifecycleStep, ...]

    @property
    def previous_requirement(self) -> str:
        return format_requirement(self.previous_pin)


def build_upgrade_plan(
    *,
    current_version: str,
    target_version: str,
    compatibility: CompatibilityReport | None = None,
    pin_kind: PinKind = PinKind.EXACT_VERSION,
) -> UpgradePlan:
    """Build a reproducible upgrade plan between two exact package versions."""
    current = parse_package_version(current_version).text
    target = parse_package_version(target_version).text
    if current == target:
        raise ValueError("upgrade requires distinct current and target versions")
    if compatibility is not None and not compatibility.is_compatible:
        raise ValueError("refusing to build upgrade plan for incompatible target contract")

    current_pin = _pin_for(current, pin_kind)
    target_pin = _pin_for(target, pin_kind)
    steps = (
        LifecycleStep(
            name="identify_current",
            description="Read the currently pinned/installed Agent Brain version.",
            requirement=format_requirement(current_pin),
        ),
        LifecycleStep(
            name="identify_target",
            description="Select the immutable target Agent Brain version.",
            requirement=format_requirement(target_pin),
        ),
        LifecycleStep(
            name="compatibility_check",
            description=(
                "Run consumer contract / public-surface checks against the target version "
                "before changing the pin."
            ),
        ),
        LifecycleStep(
            name="upgrade_install",
            description="Install the target pin (exact version, matching git tag, or commit).",
            requirement=format_requirement(target_pin),
        ),
        LifecycleStep(
            name="consumer_smoke",
            description="Run the consumer smoke against the newly installed version.",
        ),
        LifecycleStep(
            name="record_success",
            description="Record the new pin and verification evidence for operators.",
            requirement=format_requirement(target_pin),
        ),
    )
    return UpgradePlan(
        current_version=current,
        target_version=target,
        current_pin=current_pin,
        target_pin=target_pin,
        steps=steps,
        compatibility=compatibility,
    )


def build_rollback_plan(
    *,
    failed_version: str,
    previous_version: str,
    pin_kind: PinKind = PinKind.EXACT_VERSION,
) -> RollbackPlan:
    """Build a rollback plan to a previously known-good exact pin."""
    failed = parse_package_version(failed_version).text
    previous = parse_package_version(previous_version).text
    if failed == previous:
        raise ValueError("rollback requires a distinct previous version")
    previous_pin = _pin_for(previous, pin_kind)
    steps = (
        LifecycleStep(
            name="remember_previous",
            description="Use the last known-good pinned Agent Brain version (already recorded).",
            requirement=format_requirement(previous_pin),
        ),
        LifecycleStep(
            name="acknowledge_failure",
            description="Stop depending on the failed target version for consumer traffic.",
            requirement=f"agent-brain=={failed}",
        ),
        LifecycleStep(
            name="reinstall_previous",
            description="Reinstall the previous immutable pin; do not reconstruct a workspace.",
            requirement=format_requirement(previous_pin),
        ),
        LifecycleStep(
            name="consumer_smoke",
            description="Re-run consumer smoke; it must pass on the previous pin.",
        ),
        LifecycleStep(
            name="record_rollback",
            description="Document the rollback pin and leave the failed version quarantined.",
            requirement=format_requirement(previous_pin),
        ),
    )
    return RollbackPlan(
        failed_version=failed,
        previous_version=previous,
        previous_pin=previous_pin,
        steps=steps,
    )


def plan_step_names(steps: Sequence[LifecycleStep]) -> tuple[str, ...]:
    return tuple(step.name for step in steps)


def _pin_for(version: str, pin_kind: PinKind) -> PinSpec:
    if pin_kind is PinKind.EXACT_VERSION:
        return PinSpec(kind=PinKind.EXACT_VERSION, version=version, reference=version)
    if pin_kind is PinKind.GIT_TAG:
        from agent_brain.distribution.version import version_git_tag

        tag = version_git_tag(version)
        return PinSpec(kind=PinKind.GIT_TAG, version=version, reference=tag)
    raise ValueError(f"upgrade/rollback plans require exact version or git tag pins, got {pin_kind}")
