"""SurrealDB Agent Memory benchmark backend (#40) — BENCHMARK_ONLY.

Live Agent Memory requires a separate Spectron/Agent-Memory HTTP service and a
mandatory Gemini embedding model (`gemini-embedding-2`). Under the #40 cost rule
(local / deterministic / no-cost preferred; no unauthorized paid APIs), fair
semantic evaluation is blocked and recorded as:

    BLOCKED_EXTERNAL_MODEL_DEPENDENCY

This module never imports surrealdb.memory into agent_brain Core. Optional SDK
probing stays inside tests/benchmark only.
"""

from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass
from typing import Any

from tests.benchmark.agent_memory_issue40.native_backend import BackendResult

AGENT_MEMORY_PACKAGE = "surrealdb-memory"
AGENT_MEMORY_VERSION = "1.0.0b1"
AGENT_MEMORY_IMPORT = "surrealdb.memory"
REQUIRED_EMBEDDING_MODEL = "gemini-embedding-2"
REQUIRED_EMBEDDING_DIM = 3072
BLOCK_REASON = "BLOCKED_EXTERNAL_MODEL_DEPENDENCY"


@dataclass(frozen=True, slots=True)
class AgentMemoryCompatibility:
    """Official compatibility evidence captured for #40."""

    package: str
    package_version: str
    import_path: str
    python_requires: str
    surrealdb_sdk_extra: str
    surrealdb_driver_note: str
    runtime_topology: str
    embedding_model: str
    embedding_dimensions: int
    external_model_dependency: str
    local_no_cost_path: bool
    in_process_library: bool
    required_services: tuple[str, ...]
    storage_requirements: tuple[str, ...]
    productive_write_verbs_present: tuple[str, ...]
    evaluation_status: str
    evidence_urls: tuple[str, ...]


COMPATIBILITY = AgentMemoryCompatibility(
    package=AGENT_MEMORY_PACKAGE,
    package_version=AGENT_MEMORY_VERSION,
    import_path=AGENT_MEMORY_IMPORT,
    python_requires=">=3.10 (Agent Brain baseline remains >=3.12)",
    surrealdb_sdk_extra="pip install --pre 'surrealdb[memory]'",
    surrealdb_driver_note=(
        "surrealdb 2.x stable has no memory extra; memory client requires surrealdb 3.x prerelease"
    ),
    runtime_topology=(
        "Separate SurrealDB Agent Memory / Spectron HTTP service in front of SurrealDB; "
        "clients call endpoint+api_key; no supported in-process embedded library"
    ),
    embedding_model=REQUIRED_EMBEDDING_MODEL,
    embedding_dimensions=REQUIRED_EMBEDDING_DIM,
    external_model_dependency="Google Gemini embeddings required deployment-wide",
    local_no_cost_path=False,
    in_process_library=False,
    required_services=(
        "SurrealDB server",
        "Spectron/Agent Memory API (ghcr.io/surrealdb/spectron or hosted)",
        "Object store (file/S3/GCS/Azure)",
        "Gemini API for embeddings",
        "LLM provider key for extraction stages (openai/anthropic/google/cerebras/openrouter)",
    ),
    storage_requirements=(
        "SurrealDB durable store for graph/vector/document memory",
        "Object store for raw document bytes",
    ),
    productive_write_verbs_present=(
        "remember",
        "remember_many",
        "reflect",
        "consolidate",
        "elaborate",
        "forget",
    ),
    evaluation_status=BLOCK_REASON,
    evidence_urls=(
        "https://surrealdb.com/docs/agent-memory",
        "https://surrealdb.com/docs/agent-memory/integrations/sdks/python",
        "https://surrealdb.com/docs/agent-memory/quickstarts/embedded",
        "https://surrealdb.com/docs/agent-memory/tuning/models-per-stage",
        "https://surrealdb.com/docs/agent-memory/reasoning/reconciliation-and-supersession",
        "https://pypi.org/project/surrealdb-memory/1.0.0b1/",
    ),
)


def probe_optional_sdk_installed() -> bool:
    """True only if the optional benchmark host already has surrealdb.memory."""
    return importlib.util.find_spec("surrealdb") is not None and (
        importlib.util.find_spec("surrealdb.memory") is not None
    )


class AgentMemoryBenchmarkBackend:
    """Blocked Agent Memory backend: never contacts paid/external services."""

    name = "surrealdb_agent_memory"

    def __init__(self, *, endpoint: str | None = None, api_key: str | None = None) -> None:
        # Explicitly ignore credentials even if present: #40 cost/safety rule.
        self._endpoint = endpoint
        self._api_key = api_key
        self._compat = COMPATIBILITY

    @property
    def compatibility(self) -> AgentMemoryCompatibility:
        return self._compat

    async def execute(self, query: dict[str, Any]) -> BackendResult:
        started = time.perf_counter()
        latency_ms = (time.perf_counter() - started) * 1000.0
        category = query.get("category")
        # Temporal / scope / live / failure categories are still not executable
        # without the Spectron service + Gemini embeddings for a fair ingest.
        detail = (
            f"{BLOCK_REASON}: fair Agent Memory ingest/recall requires Spectron service "
            f"and mandatory {REQUIRED_EMBEDDING_MODEL}; no authorized no-cost local path. "
            f"Query category={category!r} not executed against live Agent Memory."
        )
        return BackendResult(
            backend=self.name,
            status=BLOCK_REASON,
            availability="unavailable",
            hits=(),
            latency_ms=latency_ms,
            detail=detail,
        )
