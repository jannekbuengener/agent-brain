from __future__ import annotations

from pathlib import Path


def test_connector_runtime_has_no_network_or_persistence_surface() -> None:
    runtime_root = Path(__file__).parents[2] / "src" / "agent_brain" / "connectors"
    source = "\n".join(path.read_text(encoding="utf-8") for path in runtime_root.glob("*.py"))

    forbidden_fragments = (
        "import requests",
        "import http",
        "urllib.request",
        "git clone",
        "git fetch",
        "git checkout",
        "git reset",
        "surrealdb",
        "CREATE ",
        "UPSERT ",
        "MERGE ",
    )

    assert all(fragment not in source for fragment in forbidden_fragments)
