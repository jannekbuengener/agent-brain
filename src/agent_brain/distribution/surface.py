"""Public package surface that consumers may treat as compatibility-relevant."""

from __future__ import annotations

import importlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import ModuleType

from agent_brain.distribution.compatibility import (
    CompatibilityReport,
    classify_surface_diff,
)

# Only top-level package exports are the stable public contract for #17.
# Submodules not listed in a package ``__all__`` remain internal and may change
# without a package major bump, unless a later slice explicitly stabilizes them.
PUBLIC_PACKAGE_MODULES: tuple[str, ...] = (
    "agent_brain",
    "agent_brain.contracts",
    "agent_brain.core",
    "agent_brain.context",
    "agent_brain.connectors",
    "agent_brain.retrieval",
    "agent_brain.evidence",
    "agent_brain.memory",
    "agent_brain.knowledge",
    "agent_brain.surrealdb",
    "agent_brain.distribution",
    "agent_brain.protocol",
    "agent_brain.capabilities",
)


@dataclass(frozen=True, slots=True)
class PublicSurfaceSnapshot:
    """Frozen map of public module → exported symbol names."""

    exports: Mapping[str, frozenset[str]]

    def symbols_for(self, module_name: str) -> frozenset[str]:
        return self.exports.get(module_name, frozenset())

    def all_symbols(self) -> frozenset[str]:
        return frozenset(
            f"{module}:{name}" for module, names in self.exports.items() for name in names
        )


def _export_names(module: ModuleType) -> frozenset[str]:
    declared = getattr(module, "__all__", None)
    if declared is None:
        return frozenset()
    if not isinstance(declared, (list, tuple)):
        raise TypeError(f"{module.__name__}.__all__ must be a list or tuple")
    names = [item for item in declared if isinstance(item, str)]
    return frozenset(names)


def snapshot_public_surface(
    modules: Iterable[str] = PUBLIC_PACKAGE_MODULES,
) -> PublicSurfaceSnapshot:
    """Import public packages and capture their declared ``__all__`` exports."""
    exports: dict[str, frozenset[str]] = {}
    for module_name in modules:
        module = importlib.import_module(module_name)
        exports[module_name] = _export_names(module)
    return PublicSurfaceSnapshot(exports=exports)


def compare_public_surfaces(
    baseline: PublicSurfaceSnapshot,
    candidate: PublicSurfaceSnapshot,
) -> CompatibilityReport:
    """Compare two public-surface snapshots for additive vs breaking changes."""
    modules = sorted(set(baseline.exports) | set(candidate.exports))
    removed: set[str] = set()
    added: set[str] = set()
    for module_name in modules:
        before = baseline.symbols_for(module_name)
        after = candidate.symbols_for(module_name)
        removed.update(f"{module_name}:{name}" for name in before - after)
        added.update(f"{module_name}:{name}" for name in after - before)
    return classify_surface_diff(removed=removed, added=added)
