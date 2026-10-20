# Entwicklung — Agent Brain

Diese Seite beschreibt nur die Repository-Baseline aus Slice 1. Fachliche Brain-Funktionen kommen in späteren, getrennten Slices.

## Voraussetzungen

- Python 3.12 oder neuer
- Git

## Frisch klonen und installieren

```bash
git clone https://github.com/jannekbuengener/agent-brain.git
cd agent-brain
python -m venv .venv
```

Virtuelle Umgebung aktivieren und danach:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Validierung

```bash
python -m ruff check .
python -m pytest -q
```

CI führt dieselben Qualitätsprüfungen auf Python 3.12, 3.13 und 3.14 aus.

## Aktuelle Modulgrenzen

```text
src/agent_brain/
├─ core/
├─ retrieval/
├─ memory/
├─ surrealdb/
└─ connectors/
```

Diese Verzeichnisse sind in Slice 1 bewusst nur importierbare Grenzen. Sie definieren noch keine fachliche API und keine endgültige Multi-Package- oder Distributionsstruktur.

- Portable Foundation folgt in #5.
- gemeinsame Source-/Index-/Evidence-Contracts folgen in #15.
- Retrieval, Memory und SurrealDB-Verhalten folgen in ihren eigenen Slices.
- Distribution, Versionierung und Consumer Contract werden erst in #17 festgelegt.

## Tests und Fixtures

- `tests/test_scaffold_smoke.py` schützt die Installierbarkeit und die minimalen Modulgrenzen.
- `tests/conftest.py` enthält kleine prozedurale Fixtures.
- `tests/fixtures/` ist für statische, deterministische, produktneutrale Fixtures reserviert.
- Claire-Parity-Tests und -Fixtures werden nicht blind kopiert, sondern nur im zuständigen Slice produktneutral übernommen oder später im Parity-Scope verglichen.

## Sicherheitsgrenzen

Die Baseline implementiert absichtlich keine Context-/Retrieval-Funktion, keine SurrealDB-Runtime, keine Agent-Workforce-Anbindung und keine produktiven Memory Writes.
