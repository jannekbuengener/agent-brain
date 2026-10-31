"""Surreal namespace/database catalog probes for the read adapter (#10 / #38).

``INFO FOR ROOT`` is an internal adapter probe, not a user-facing statement
(the public statement guard denies it). Results are mapped without leaking
user hashes or secrets.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from agent_brain.surrealdb.http import SurrealHttpProbeResult, parse_json_body, post_sql

SqlExecutor = Callable[..., SurrealHttpProbeResult]


@dataclass(frozen=True, slots=True)
class CatalogProbe:
    """Namespace/database existence relative to configured mapping."""

    reachable: bool
    namespaces: frozenset[str] = frozenset()
    namespace_present: bool | None = None
    database_present: bool | None = None
    detail: str | None = None


def _namespace_names_from_root_info(payload: Any) -> frozenset[str]:
    if not isinstance(payload, list) or not payload:
        return frozenset()
    first = payload[0]
    if not isinstance(first, Mapping):
        return frozenset()
    result = first.get("result")
    if not isinstance(result, Mapping):
        return frozenset()
    namespaces = result.get("namespaces")
    if not isinstance(namespaces, Mapping):
        return frozenset()
    return frozenset(str(name) for name in namespaces)


def _database_names_from_ns_info(payload: Any) -> frozenset[str]:
    if not isinstance(payload, list) or not payload:
        return frozenset()
    # USE + INFO may return multiple result rows; take last OK INFO payload.
    for entry in reversed(payload):
        if not isinstance(entry, Mapping):
            continue
        if entry.get("status") not in (None, "OK"):
            continue
        result = entry.get("result")
        if not isinstance(result, Mapping):
            continue
        databases = result.get("databases")
        if isinstance(databases, Mapping):
            return frozenset(str(name) for name in databases)
    return frozenset()


def probe_configured_catalog(
    *,
    endpoint: str,
    namespace: str,
    database: str,
    timeout_seconds: float,
    sql_executor: SqlExecutor | None = None,
) -> CatalogProbe:
    """Probe whether the configured namespace/database exist.

    Uses internal ``INFO FOR ROOT`` then ``INFO FOR NS`` when the namespace is
    present. Transport failures yield ``reachable=False`` and unknown presence.
    """
    executor = sql_executor or post_sql
    root = executor(
        endpoint,
        "INFO FOR ROOT;",
        namespace="",
        database="",
        timeout_seconds=timeout_seconds,
    )
    if not root.ok:
        return CatalogProbe(
            reachable=False,
            detail=root.error or f"INFO FOR ROOT failed ({root.status_code})",
        )

    namespaces = _namespace_names_from_root_info(parse_json_body(root.body_text))
    if namespace not in namespaces:
        return CatalogProbe(
            reachable=True,
            namespaces=namespaces,
            namespace_present=False,
            database_present=False,
            detail=f"configured namespace {namespace!r} absent",
        )

    ns_info = executor(
        endpoint,
        "INFO FOR NS;",
        namespace=namespace,
        database=database,
        timeout_seconds=timeout_seconds,
    )
    if not ns_info.ok:
        return CatalogProbe(
            reachable=True,
            namespaces=namespaces,
            namespace_present=True,
            database_present=None,
            detail=ns_info.error or f"INFO FOR NS failed ({ns_info.status_code})",
        )

    databases = _database_names_from_ns_info(parse_json_body(ns_info.body_text))
    db_present = database in databases
    return CatalogProbe(
        reachable=True,
        namespaces=namespaces,
        namespace_present=True,
        database_present=db_present,
        detail=None
        if db_present
        else f"configured database {database!r} absent in namespace {namespace!r}",
    )
