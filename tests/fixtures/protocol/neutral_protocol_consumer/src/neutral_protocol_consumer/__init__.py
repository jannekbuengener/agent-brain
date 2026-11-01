"""Neutral consumer smoke for Agent Brain Genericity Proof (#19).

No Claire business logic, trading types, Claire configs, or Claire fixtures.
Exercises the public protocol surface only, including clean-env install paths.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from importlib import metadata

from agent_brain.memory import (
    MEMORY_RECORD_SCHEMA,
    MEMORY_SCOPE_SCHEMA,
    InMemoryMemoryStore,
    MemoryRecord,
    MemoryScope,
    MemoryScopeKind,
)
from agent_brain.protocol import (
    ProtocolErrorCode,
    ProtocolGateway,
    ProtocolRequest,
    ProtocolRuntime,
    invoke,
)


def smoke(pinned_version: str) -> dict[str, object]:
    installed = metadata.version("agent-brain")
    if installed != pinned_version:
        raise RuntimeError(f"version mismatch: installed={installed} pinned={pinned_version}")

    # Refuse accidental Claire/CDB packages in the clean environment.
    for banned in ("claire", "claire_de_binare", "cdb", "core"):
        try:
            metadata.version(banned)
        except metadata.PackageNotFoundError:
            continue
        raise RuntimeError(f"forbidden package present in clean env: {banned}")

    version = invoke("version")
    if not version.ok:
        raise RuntimeError("version operation failed")
    assert version.data is not None
    if version.data["agent_brain_version"] != pinned_version:
        raise RuntimeError("protocol version metadata mismatch")

    caps = invoke("capabilities")
    if not caps.ok or caps.data is None:
        raise RuntimeError("capabilities operation failed")
    available = {
        item["capability"]
        for item in caps.data["capabilities"]
        if item["state"] == "available"
    }
    for required in ("context_read", "retrieval", "evidence"):
        if required not in available:
            raise RuntimeError(f"expected {required} capability")

    context = invoke(
        "context_read",
        {
            "mode": "package",
            "target_scope": "docs:handbook",
            "source_priority": {"ordered_sources": ["docs"]},
            "artifacts": [
                {
                    "ref": {
                        "schema_version": "artifact-ref/v1",
                        "artifact_id": "handbook-1",
                        "source_id": "docs",
                        "source_path": "handbook/intro.md",
                        "source_hash": "neutralhash",
                    },
                    "artifact_type": "doc",
                    "summary": "neutral handbook intro",
                    "payload": {"note": "documentation workspace"},
                }
            ],
            "generated_at_or_as_of": "2026-10-31T12:00:00Z",
        },
    )
    if not context.ok:
        raise RuntimeError("context_read failed")

    retrieval = invoke(
        "retrieval",
        {
            "query": {
                "schema_version": "retrieval-query/v1",
                "query_id": "neutral-q1",
                "query_text": "handbook",
                "source_id": "docs",
            },
            "records": [
                {
                    "schema_version": "index-record/v1",
                    "record_id": "rec-handbook",
                    "record_type": "doc",
                    "source": {
                        "schema_version": "artifact-ref/v1",
                        "artifact_id": "handbook-1",
                        "source_id": "docs",
                        "source_path": "handbook/intro.md",
                        "source_hash": "neutralhash",
                    },
                    "content_hash": "content-neutral",
                    "attributes": {
                        "title": "handbook intro",
                        "text": "how to use the documentation handbook",
                    },
                }
            ],
            "source_priority": ["docs"],
        },
    )
    if not retrieval.ok:
        raise RuntimeError("retrieval failed")

    evidence = invoke("evidence", {"scope": "docs:handbook", "topic": "trust"})
    if not evidence.ok or evidence.data is None or "trust_summary" not in evidence.data:
        raise RuntimeError("evidence/trust failed")

    # Structured failure: unbound memory must not look like empty success.
    failure = invoke("memory_read", {"scope": None, "as_of": "2026-10-31T12:00:00Z"})
    if failure.ok:
        raise RuntimeError("memory_read should fail without a store/scope")
    assert failure.error is not None
    if failure.error.code not in {
        ProtocolErrorCode.CAPABILITY_UNAVAILABLE,
        ProtocolErrorCode.INVALID_SCOPE,
    }:
        raise RuntimeError(f"unexpected failure code: {failure.error.code}")

    # Memory read success path via public InMemory adapter (still Claire-free).
    scope = MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.TENANT,
        tenant_id="docs-tenant",
    )
    record = MemoryRecord(
        schema_version=MEMORY_RECORD_SCHEMA,
        record_id="mem-1",
        subject_ref="subject:handbook",
        scope=scope,
        content_ref="content:mem-1",
        known_at=datetime(2026, 10, 31, 11, 0, 0),
        summary="prior handbook note",
    )
    runtime = ProtocolRuntime(memory_store=InMemoryMemoryStore(records=(record,)))
    memory_ok = ProtocolGateway(runtime).invoke_sync(
        ProtocolRequest(
            operation="memory_read",
            payload={
                "scope": {
                    "schema_version": MEMORY_SCOPE_SCHEMA,
                    "kind": "tenant",
                    "tenant_id": "docs-tenant",
                },
                "as_of": "2026-10-31T12:00:00Z",
                "query_id": "neutral-memory",
            },
        )
    )
    if not memory_ok.ok or memory_ok.data is None:
        raise RuntimeError("memory_read with bound store failed")
    result = memory_ok.data.get("result") or {}
    if result.get("availability") not in {"available", "empty"}:
        # empty is acceptable when filters exclude; available preferred with record
        raise RuntimeError(f"unexpected memory availability: {result.get('availability')}")

    # CLI path after console-script install.
    completed = subprocess.run(
        [sys.executable, "-m", "agent_brain.cli", "version", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    cli_payload = json.loads(completed.stdout)
    if cli_payload["data"]["agent_brain_version"] != pinned_version:
        raise RuntimeError("CLI version drift")

    return {
        "pinned_version": pinned_version,
        "installed_version": installed,
        "available_capabilities": sorted(available),
        "context_ok": True,
        "retrieval_ok": True,
        "evidence_ok": True,
        "memory_read_ok": True,
        "failure_code": failure.error.code.value,
        "cli_version": cli_payload["data"]["agent_brain_version"],
        "claire_packages_absent": True,
    }


__all__ = ["smoke"]
