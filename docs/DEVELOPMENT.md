# Entwicklung — Agent Brain

Diese Seite beschreibt die installierbare Repository-Baseline, die Portable Foundation, die gemeinsamen Source-/Index-/Evidence-Contracts und den produktneutralen Context-/Briefing-Core. Retrieval-, Memory-, Ingestion- und Datenbank-Runtime folgen weiterhin in getrennten Slices.

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
├─ context/
│  ├─ briefing.py
│  ├─ explanation.py
│  ├─ package.py
│  ├─ required_reads.py
│  └─ validation.py
├─ retrieval/
├─ memory/
├─ surrealdb/
└─ connectors/
```

`core/` besitzt die Portable Foundation. `contracts/` besitzt die gemeinsamen, versionierten Datenverträge. `context/` besitzt den side-effect-freien Context-Package-/Briefing-Kern. Die übrigen Verzeichnisse bleiben bewusst importierbare Grenzen ohne vorgezogene fachliche Runtime.

- Foundation-Verträge: [foundation/README.md](foundation/README.md)
- gemeinsame Contracts: [contracts/README.md](contracts/README.md)
- Context / Briefing: [context/README.md](context/README.md)
- externe Referenzen und ihre Live-Relevanz: [external-docs/index.md](external-docs/index.md)
- Repository Ingestion folgt in #9.
- Retrieval, Memory und SurrealDB-Verhalten folgen in ihren eigenen Slices.
- Distribution, Versionierung und Consumer Contract werden erst in #17 festgelegt.

## Tests und Fixtures

- `tests/test_scaffold_smoke.py` schützt die Installierbarkeit und die minimalen Modulgrenzen.
- `tests/core/` schützt die produktneutralen Foundation-Verträge und deterministischen Charakterisierungen.
- `tests/contracts/` schützt Schema-Versionierung, Round-Trips, additive v1-Kompatibilität und strukturelle Source-/Index-/Evidence-Verträge.
- `tests/context/` schützt Context Package, Required Reads, Self-Explanation, Validation, Briefing und die öffentliche Slice-4-API.
- `tests/fixtures/contracts/` enthält statische, deterministische, produktneutrale Contract-Fixtures.
- `tests/fixtures/context/` enthält neutrale Context-/Briefing-Fixtures.
- `tests/conftest.py` enthält kleine prozedurale Fixtures.
- Claire-Parity-Tests und -Fixtures werden nicht blind kopiert, sondern nur im zuständigen Slice produktneutral charakterisiert oder später im Parity-Scope verglichen.

## Sicherheitsgrenzen

Die aktuelle Baseline implementiert keine Repository-Ingestion, kein Retrieval, keine SurrealDB-Runtime, keine Agent-Workforce-Anbindung und keine produktiven Memory Writes. Der Context-/Briefing-Core führt keine externen Aktionen aus und besitzt keine Produktfreigabe-Autorität. `EvidenceRef` und `ClaimRef` transportieren weiterhin nur Identität und Beziehungen; Trust, Resolver und Scoring folgen erst in Slice #8. Produktpolicy bleibt außerhalb des generischen Kerns und kann nur über neutrale Policy-Hooks injiziert werden.
