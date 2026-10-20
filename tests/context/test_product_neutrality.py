from __future__ import annotations

from pathlib import Path

RUNTIME_ROOT = Path("src/agent_brain/context")
FIXTURE_ROOT = Path("tests/fixtures/context")
FORBIDDEN = (
    "claire",
    "cdb_",
    "trading",
    "echtgeld",
    "live-go",
    "lr-",
    "surrealdb-local",
    "mexc",
)


def test_context_runtime_and_neutral_fixtures_have_no_product_leakage() -> None:
    files = sorted(RUNTIME_ROOT.glob("*.py")) + sorted(FIXTURE_ROOT.glob("*"))
    assert files

    leaks: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8").casefold()
        for forbidden in FORBIDDEN:
            if forbidden.casefold() in text:
                leaks.append(f"{path}:{forbidden}")

    assert leaks == []
