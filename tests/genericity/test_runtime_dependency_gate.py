"""Static runtime dependency gate for #19 genericity proof.

Focuses on installable package code under ``src/agent_brain``. Historical docs,
frozen inventory evidence, and comments may mention Claire without constituting
a runtime dependency. Import graphs must stay free of Claire / CDB / trading /
private ``core.*`` packages.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "agent_brain"

# Top-level modules that would constitute a hidden product runtime dependency.
FORBIDDEN_TOP_LEVEL_IMPORTS = frozenset(
    {
        "claire",
        "claire_de_binare",
        "cdb",
        "cdb_core",
        "core",  # private Claire core.*; agent_brain.core is local and allowed
        "services",
        "tools",
    }
)

FORBIDDEN_ABSOLUTE_PREFIXES = (
    "claire.",
    "claire_de_binare.",
    "cdb.",
    "core.",
    "services.",
    "tools.",
)

# Product markers that must not appear as required runtime identifiers in
# package source outside explicitly allowlisted evidence / comment contexts.
RUNTIME_PRODUCT_MARKERS = (
    "echtgeld",
    "live-go",
    "mexc",
    "kill_switch",
)


def _iter_runtime_py_files() -> list[Path]:
    return sorted(path for path in SRC_ROOT.rglob("*.py") if path.is_file())


def _module_is_forbidden(module: str) -> bool:
    top = module.split(".", 1)[0]
    if top == "agent_brain":
        return False
    if top in FORBIDDEN_TOP_LEVEL_IMPORTS:
        return True
    return any(module == prefix[:-1] or module.startswith(prefix) for prefix in FORBIDDEN_ABSOLUTE_PREFIXES)


def test_runtime_import_graph_has_no_claire_cdb_or_trading_packages() -> None:
    hits: list[str] = []
    for path in _iter_runtime_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _module_is_forbidden(alias.name):
                        hits.append(f"{path.relative_to(REPO_ROOT)}:import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.level and not node.module:
                    continue  # relative import inside agent_brain
                if node.module and _module_is_forbidden(node.module):
                    # Relative imports (level>0) stay inside the package.
                    if node.level:
                        continue
                    hits.append(f"{path.relative_to(REPO_ROOT)}:from {node.module}")
    assert hits == []


def test_surreal_read_settings_defaults_are_product_neutral() -> None:
    from agent_brain.surrealdb import SurrealDbReadSettings

    settings = SurrealDbReadSettings()
    lowered_ns = settings.namespace.casefold()
    lowered_db = settings.database.casefold()
    for banned in ("cdb", "claire", "trading", "mexc"):
        assert banned not in lowered_ns
        assert banned not in lowered_db


def test_runtime_source_has_no_trading_or_live_markers_outside_allowlist() -> None:
    """Hard product markers must not appear in runtime identifiers/strings.

    Frozen Surreal inventory evidence under ``surrealdb/runtime_truth.py`` may
    document Claire volume names as historical inventory facts — those are
    classified as HISTORICAL_REFERENCE, not runtime coupling, and are allowlisted.
    """
    allowlisted = {
        (SRC_ROOT / "surrealdb" / "runtime_truth.py").resolve(),
        (SRC_ROOT / "surrealdb" / "statement_guard.py").resolve(),
        (SRC_ROOT / "surrealdb" / "config.py").resolve(),
        (SRC_ROOT / "protocol" / "runtime.py").resolve(),
        (SRC_ROOT / "cli" / "__init__.py").resolve(),
        (SRC_ROOT / "distribution" / "__init__.py").resolve(),
    }
    # Docstring/comment mentions of extraction history are OK in modules that
    # only negate Claire coupling; allowlist those known negation modules.
    hits: list[str] = []
    for path in _iter_runtime_py_files():
        if path.resolve() in allowlisted:
            continue
        text = path.read_text(encoding="utf-8").casefold()
        for marker in RUNTIME_PRODUCT_MARKERS:
            if marker in text:
                hits.append(f"{path.relative_to(REPO_ROOT)}:{marker}")
    assert hits == []


def test_pyproject_has_no_claire_or_cdb_runtime_dependencies() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8").casefold()
    # dependencies = [] is expected; refuse accidental product deps.
    for banned in ("claire", "cdb-", "mexc", "trading"):
        assert banned not in pyproject
