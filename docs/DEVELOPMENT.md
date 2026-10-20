# Entwicklung — Agent Brain

Diese Seite beschreibt die installierbare Repository-Baseline, die Portable Foundation und die gemeinsamen Source-/Index-/Evidence-Contracts. Retrieval-, Context-, Memory- und Datenbank-Runtime folgen weiterhin in getrennten Slices.

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
│  ├─ run_id.py
│  ├─ source_priority.py
│  └─ time.py
├─ contracts/
│  ├─ evidence.py
│  ├─ index.py
│  ├─ registry.py
│  ├─ repository.py
│  ├─ serialization.py
│  └─ versioning.py
├─ retrieval/
├─ memory/
├─ surrealdb/
└─ connectors/
```

`core/` besitzt die Portable Foundation. `contracts/` besitzt die gemeinsamen, versionierten Datenverträge. Die übrigen Verzeichnisse bleiben bewusst importierbare Grenzen ohne vorgezogene fachliche Runtime.

- Foundation-Verträge: [foundation/README.md](foundation/README.md)
- gemeinsame Contracts: [contracts/README.md](contracts/README.md)
- Context / Briefing folgt in #6.
- Retrieval, Memory und SurrealDB-Verhalten folgen in ihren eigenen Slices.
- Distribution, Versionierung und Consumer Contract werden erst in #17 festgelegt.

## Tests und Fixtures

- `tests/test_scaffold_smoke.py` schützt die Installierbarkeit und die minimalen Modulgrenzen.
- `tests/core/` schützt die produktneutralen Foundation-Verträge und deterministischen Charakterisierungen.
- `tests/contracts/` schützt Schema-Versionierung, Round-Trips, additive v1-Kompatibilität und strukturelle Source-/Index-/Evidence-Verträge.
- `tests/fixtures/contracts/` enthält statische, deterministische, produktneutrale Contract-Fixtures.
- `tests/conftest.py` enthält kleine prozedurale Fixtures.
- Claire-Parity-Tests und -Fixtures werden nicht blind kopiert, sondern nur im zuständigen Slice produktneutral übernommen oder später im Parity-Scope verglichen.

## Sicherheitsgrenzen

Die aktuelle Baseline implementiert keine Repository-Ingestion, kein Retrieval, kein Context Package, keine SurrealDB-Runtime, keine Agent-Workforce-Anbindung und keine produktiven Memory Writes. `EvidenceRef` und `ClaimRef` transportieren nur Identität und Beziehungen; Trust, Resolver und Scoring folgen erst in Slice #8. Produktpolicy bleibt außerhalb des generischen Kerns.
