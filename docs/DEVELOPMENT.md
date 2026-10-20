# Entwicklung — Agent Brain

Diese Seite beschreibt die installierbare Repository-Baseline und die Portable Foundation. Fachliche Repository-, Retrieval-, Context-, Memory- und Datenbank-Verträge folgen in getrennten Slices.

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
│  ├─ canonical.py
│  ├─ identity.py
│  ├─ policy.py
│  ├─ redaction.py
│  ├─ source_priority.py
│  └─ time.py
├─ retrieval/
├─ memory/
├─ surrealdb/
└─ connectors/
```

Nur `core/` besitzt in der aktuellen Baseline fachliche Foundation-Primitiven. Die übrigen Verzeichnisse bleiben bewusst importierbare Grenzen ohne vorgezogene Runtime.

- Foundation-Verträge: [foundation/README.md](foundation/README.md)
- gemeinsame Source-/Index-/Evidence-Contracts folgen in #15.
- Retrieval, Memory und SurrealDB-Verhalten folgen in ihren eigenen Slices.
- Distribution, Versionierung und Consumer Contract werden erst in #17 festgelegt.

## Tests und Fixtures

- `tests/test_scaffold_smoke.py` schützt die Installierbarkeit und die minimalen Modulgrenzen.
- `tests/core/` schützt die produktneutralen Foundation-Verträge und deterministischen Charakterisierungen.
- `tests/conftest.py` enthält kleine prozedurale Fixtures.
- `tests/fixtures/` ist für statische, deterministische, produktneutrale Fixtures reserviert.
- Claire-Parity-Tests und -Fixtures werden nicht blind kopiert, sondern nur im zuständigen Slice produktneutral übernommen oder später im Parity-Scope verglichen.

## Sicherheitsgrenzen

Die Foundation implementiert absichtlich keine Repository-/Evidence-Domaincontracts aus #15, kein Retrieval, kein Context Package, keine SurrealDB-Runtime, keine Agent-Workforce-Anbindung und keine produktiven Memory Writes. Produktpolicy wird ausschließlich über injizierbare Hooks vorbereitet und nicht im Core fest verdrahtet.
