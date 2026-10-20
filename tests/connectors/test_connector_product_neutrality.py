from __future__ import annotations

from pathlib import Path


def test_connector_runtime_and_neutral_fixtures_contain_no_product_policy() -> None:
    root = Path(__file__).resolve().parents[2]
    targets = [root / "src" / "agent_brain" / "connectors"]
    targets.append(root / "tests" / "fixtures" / "connectors" / "repository_neutral")
    forbidden = ("claire_de_binare", "trading", "echtgeld", "live-go", "mexc", "cdb_")

    for target in targets:
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            rendered = path.read_text(encoding="utf-8", errors="ignore").lower()
            assert not any(term in rendered for term in forbidden), path
