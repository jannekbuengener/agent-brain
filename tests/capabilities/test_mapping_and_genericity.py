"""Mapping uniqueness + genericity boundary for cdb_context foundation."""

from __future__ import annotations

import ast
from pathlib import Path

from agent_brain.capabilities import (
    CAPABILITY_MAPPINGS,
    REQUIRED_CAPABILITY_NAMES,
    BackendKind,
    CapabilityGateway,
    invoke_capability,
)
from agent_brain.capabilities.names import CDB_CONTEXT_BRIEFING

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "agent_brain"
GENERIC_PACKAGES = (
    "core",
    "context",
    "contracts",
    "retrieval",
    "evidence",
    "memory",
    "connectors",
    "knowledge",
    "distribution",
    "protocol",
    "cli",
)


def test_each_required_capability_has_exactly_one_mapping() -> None:
    assert set(CAPABILITY_MAPPINGS) >= set(REQUIRED_CAPABILITY_NAMES)
    targets = [
        (
            item.backend_kind,
            item.protocol_operation,
            item.domain_symbol,
        )
        for name, item in CAPABILITY_MAPPINGS.items()
        if name in REQUIRED_CAPABILITY_NAMES
    ]
    assert len(targets) == len(set(targets))
    assert CAPABILITY_MAPPINGS[CDB_CONTEXT_BRIEFING].protocol_operation == "context_read"
    assert CAPABILITY_MAPPINGS["cdb_context.search"].protocol_operation == "retrieval"
    assert CAPABILITY_MAPPINGS["cdb_context.evidence"].protocol_operation == "evidence"
    assert (
        CAPABILITY_MAPPINGS["cdb_context.required_reads"].backend_kind
        is BackendKind.DOMAIN_PRIMITIVE
    )


def test_generic_packages_do_not_import_cdb_context_profile() -> None:
    hits: list[str] = []
    for package in GENERIC_PACKAGES:
        root = SRC_ROOT / package
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and (
                    "capabilities.cdb_context" in node.module
                    or node.module.endswith("capabilities.cdb_context")
                ):
                    hits.append(str(path.relative_to(REPO_ROOT)))
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "capabilities.cdb_context" in alias.name:
                            hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == []


def test_generic_core_has_no_claire_runtime_imports() -> None:
    forbidden_prefixes = ("claire", "claire_de_binare", "cdb.", "cdb_core")
    hits: list[str] = []
    for package in ("core", "context", "retrieval", "evidence", "memory", "protocol"):
        for path in (SRC_ROOT / package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    modules.append(node.module)
                for module in modules:
                    top = module.split(".", 1)[0]
                    if top in {"claire", "claire_de_binare", "cdb", "cdb_core"}:
                        hits.append(f"{path.relative_to(REPO_ROOT)}:{module}")
                    if any(module.startswith(prefix) for prefix in forbidden_prefixes):
                        hits.append(f"{path.relative_to(REPO_ROOT)}:{module}")
    assert hits == []


def test_capability_gateway_reuses_protocol_health() -> None:
    from agent_brain.protocol import invoke as protocol_invoke

    protocol = protocol_invoke("health")
    capability = invoke_capability("agent_brain.health")
    assert capability.ok is protocol.ok
    assert capability.data is not None
    assert capability.data["overall"] == protocol.data["overall"]
    assert capability.data["components"] == protocol.data["components"]


def test_no_trading_or_execution_authority_in_cdb_profile_guardrails() -> None:
    from agent_brain.capabilities.cdb_context import CDB_GUARDRAILS

    joined = " ".join(CDB_GUARDRAILS).casefold()
    assert "does not authorize execution" in joined
    assert "authorized to trade" not in joined
    assert "go_token" not in joined
    assert CapabilityGateway is not None  # gateway remains importable with profile
