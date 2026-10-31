from pathlib import Path

FORBIDDEN = ("claire", "trading", "surrealdb", "mexc")

def test_evidence_modules_product_neutral():
    root = Path("src/agent_brain/evidence")
    leaks = []
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8").casefold()
        for word in FORBIDDEN:
            if word in text:
                leaks.append(f"{path}:{word}")
    assert leaks == []
