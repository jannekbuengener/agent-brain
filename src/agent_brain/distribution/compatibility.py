"""Compatibility rules for package and public-contract changes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum


class ChangeKind(str, Enum):
    """How a change affects external consumers."""

    ADDITIVE = "additive"
    BREAKING = "breaking"
    DEPRECATION = "deprecation"
    INTERNAL = "internal"


class CompatibilityVerdict(str, Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    """Machine-checkable compatibility result for a surface or expectation diff."""

    verdict: CompatibilityVerdict
    kind: ChangeKind
    removed: frozenset[str] = field(default_factory=frozenset)
    added: frozenset[str] = field(default_factory=frozenset)
    missing_expected: frozenset[str] = field(default_factory=frozenset)
    notes: tuple[str, ...] = ()

    @property
    def is_compatible(self) -> bool:
        return self.verdict is CompatibilityVerdict.COMPATIBLE


def classify_surface_diff(
    *,
    removed: Iterable[str],
    added: Iterable[str],
) -> CompatibilityReport:
    """Classify a public-surface diff.

    Rules (package SemVer / consumer contract):
    - removing or renaming a public export is **breaking**
    - adding a public export is **additive**
    - empty diff is additive/compatible (no consumer impact)
    """
    removed_set = frozenset(removed)
    added_set = frozenset(added)
    if removed_set:
        return CompatibilityReport(
            verdict=CompatibilityVerdict.INCOMPATIBLE,
            kind=ChangeKind.BREAKING,
            removed=removed_set,
            added=added_set,
            notes=(
                "Removing or renaming a public export breaks pinned consumers.",
                "Bump the package major version and document a migration.",
            ),
        )
    if added_set:
        return CompatibilityReport(
            verdict=CompatibilityVerdict.COMPATIBLE,
            kind=ChangeKind.ADDITIVE,
            removed=removed_set,
            added=added_set,
            notes=("New public exports are additive for existing consumers.",),
        )
    return CompatibilityReport(
        verdict=CompatibilityVerdict.COMPATIBLE,
        kind=ChangeKind.ADDITIVE,
        notes=("Public surface unchanged.",),
    )


def evaluate_consumer_expectations(
    *,
    expected_exports: Mapping[str, Iterable[str]],
    actual_exports: Mapping[str, Iterable[str]],
) -> CompatibilityReport:
    """Fail closed when a consumer-required public export is missing."""
    missing: set[str] = set()
    for module_name, names in expected_exports.items():
        actual = frozenset(actual_exports.get(module_name, ()))
        for name in names:
            if name not in actual:
                missing.add(f"{module_name}:{name}")
    if missing:
        return CompatibilityReport(
            verdict=CompatibilityVerdict.INCOMPATIBLE,
            kind=ChangeKind.BREAKING,
            missing_expected=frozenset(missing),
            notes=("Consumer expected public exports that are absent.",),
        )
    return CompatibilityReport(
        verdict=CompatibilityVerdict.COMPATIBLE,
        kind=ChangeKind.ADDITIVE,
        notes=("All consumer-expected public exports are present.",),
    )


# Explicit change taxonomy for documentation and later #12/#13 consumption.
CHANGE_RULES: dict[ChangeKind, str] = {
    ChangeKind.ADDITIVE: (
        "Existing public exports, structured contracts, and install requirements keep "
        "their meaning. New optional fields/symbols/dependencies may appear. Compatible "
        "with a minor or patch bump."
    ),
    ChangeKind.BREAKING: (
        "A public export is removed/renamed, a structured contract changes incompatibly, "
        "required install constraints tighten in a way that rejects previously supported "
        "environments, or identity/semantics of a pinned contract change. Requires a "
        "major version bump."
    ),
    ChangeKind.DEPRECATION: (
        "A public export remains available but is announced for later removal. Consumers "
        "must migrate before the next breaking major. Deprecations are documented and "
        "still pass compatibility checks until removed."
    ),
    ChangeKind.INTERNAL: (
        "Modules, helpers, and fixtures outside the declared public surface may change "
        "freely without a package major bump."
    ),
}
