"""Neutral consumer smoke for Agent Brain CLI / Protocol Surface (#12).

No Claire business logic. Exercises the public protocol surface only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from importlib import metadata

from agent_brain.protocol import ProtocolErrorCode, invoke


def smoke(pinned_version: str) -> dict[str, object]:
    installed = metadata.version("agent-brain")
    if installed != pinned_version:
        raise RuntimeError(f"version mismatch: installed={installed} pinned={pinned_version}")

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
    if "context_read" not in available:
        raise RuntimeError("expected context_read capability")

    context = invoke(
        "context_read",
        {
            "mode": "package",
            "target_scope": "consumer:smoke",
            "source_priority": {"ordered_sources": ["repo"]},
            "artifacts": [
                {
                    "ref": {
                        "schema_version": "artifact-ref/v1",
                        "artifact_id": "smoke-1",
                        "source_id": "repo",
                        "source_path": "README.md",
                        "source_hash": "smokehash",
                    },
                    "artifact_type": "doc",
                    "summary": "smoke",
                    "payload": {"note": "neutral"},
                }
            ],
            "generated_at_or_as_of": "2026-10-31T12:00:00Z",
        },
    )
    if not context.ok:
        raise RuntimeError("context_read failed")

    failure = invoke("memory_read", {"scope": None, "as_of": "2026-10-31T12:00:00Z"})
    if failure.ok:
        raise RuntimeError("memory_read should fail without a store/scope")
    assert failure.error is not None
    if failure.error.code not in {
        ProtocolErrorCode.CAPABILITY_UNAVAILABLE,
        ProtocolErrorCode.INVALID_SCOPE,
    }:
        raise RuntimeError(f"unexpected failure code: {failure.error.code}")

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
        "failure_code": failure.error.code.value,
        "cli_version": cli_payload["data"]["agent_brain_version"],
    }


__all__ = ["smoke"]
