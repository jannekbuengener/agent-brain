# Agent-Brain Arbeitsregeln

Diese Datei gilt für Agenten und Menschen, die in diesem Repository Änderungen vornehmen.

## Ziel des Repositories

`agent-brain` wird als generischer Kontext-, Evidence-, Memory-, Retrieval- und Knowledge-Kern aus Claire de Binare extrahiert. GitHub- und Repo-Live-State bleiben die oberste Wahrheit; Agent Brain ist keine Autorität für Produkt-, Trading- oder Live-Entscheidungen.

## Pflicht-Lesepfad

Vor Implementierungsarbeit mindestens lesen:

1. `README.md`
2. `docs/START_HIER.md`
3. das aktuelle GitHub-Issue
4. `docs/extraction/SLICE_0_EXTRACTION_CANON.md`
5. bei Ownership-Fragen `docs/extraction/COMPONENT_OWNERSHIP.md`
6. bei Test-/Parity-Fragen `docs/extraction/PARITY_GATES.md`
7. bei persistiertem State `docs/extraction/STATE_TRANSITION.md`
8. bei Dependency-, CI-, Protocol-, DB- oder externen Tooling-Fragen `docs/external-docs/index.md`

Externe Dokumentation erklärt Upstream-Technologien, ersetzt aber niemals GitHub-/Repo-Live-State oder einen kanonischen Agent-Brain-Contract. Im externen Referenzindex sind `P0`/`P1`-Einträge durch aktuelle Repo-Evidence belegt; `P2` ist geparkt/reference-only und darf nicht als vorhandene Runtime-Fähigkeit oder Dependency interpretiert werden.

## Wahrheitshierarchie

1. GitHub Live
2. Repo Live
3. verifizierte Context-/DB-Evidence
4. kanonische Projektdateien
5. Ledger-/Statusdateien
6. Memory oder frühere Agentenberichte

Niedrigere Quellen dürfen höhere, aktuellere Quellen nicht überschreiben.

## Scope-Grenzen

- Claire-Code nicht blind kopieren; bestehendes Verhalten wird nur im dafür vorgesehenen Slice produktneutral extrahiert.
- `MOVE`, `ADAPTER`, `STAY` und `DEFER` aus dem Extraction Canon bleiben verbindlich.
- Slice #5 besitzt die Portable Foundation; Slice #15 besitzt gemeinsame Source-/Index-/Evidence-Contracts. Frühere Slices dürfen diese APIs nicht vorwegnehmen.
- Keine funktionale Retrieval-, Context-, SurrealDB- oder Memory-Runtime ohne passendes Issue.
- **Gemeinsame Arbeits-Handoffs sind erlaubt:** Die durch [#94](https://github.com/jannekbuengener/agent-brain/issues/94) explizit freigegebene, eng typisierte lokale `agent-brain-handoff write/read`-Oberfläche darf Agenten-Arbeitsstände append-only in der eigenen SurrealDB (`agent_brain/shared_memory`) speichern und wieder abrufen. Kein individueller Human-GO für jeden gewöhnlichen Arbeitsstand; keine Secrets/Trading-State und keine automatische Live-Aktion. Einstieg: `docs/operations/SHARED_MEMORY.md`.
- **Unbeschränkte, generische Agent-Memory-Writes** (`remember/reflect/consolidate`, freie DB-Mutationen und Remote-Consumer ohne pro-Repo-Auth) bleiben `DEFER`. Die bestehenden `MemoryStore`/`KnowledgeStore`-Ports bleiben read-only. Handoff darf diese Guards nicht umgehen.
- Keine Agent-Workforce-Produktintegration in der Scaffold-Baseline.
- Keine Secrets, Trading-Runtime-Daten oder produktiven State-Mutationen.
- Der private ChatGPT-MCP ist keine Repo-Abhängigkeit und darf in Tests, CI oder Worker-Anweisungen nicht vorausgesetzt werden.

## Python- und Packaging-Baseline

- Python: `>=3.12`
- Layout: `src/agent_brain/`
- Slice 1 hat keine Runtime-Dependencies.
- `core`, `retrieval`, `memory`, `surrealdb` und `connectors` sind zunächst nur Modulgrenzen, keine vorgezogenen fachlichen APIs.
- Version-Quelle: `pyproject.toml` `[project].version` (kanonisiert in #17); Runtime über `agent_brain.__version__` / `importlib.metadata`. Git-Tag-Konvention: `v{version}`.

## Entwicklung und Validierung

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

Neue fachliche Implementierung folgt test-first. Statische Fixtures liegen unter `tests/fixtures/`; prozedurale Fixtures nur sparsam in `tests/conftest.py` oder modulnahen `conftest.py`-Dateien.

## Git-/PR-Regel

- Keine direkte Implementierung auf `main`.
- Für Änderungen isolierten Branch oder Worktree verwenden.
- Diff gegen das zugehörige Issue prüfen.
- Required Checks müssen grün sein, bevor gemergt wird.
- Issues erst nach live verifiziertem Merge und vollständiger Acceptance schließen.

## Dokumentation

GitHub-facing Dokumentation ist Human First und standardmäßig deutsch. Maschinenverträge, Python-Symbole, Schemas und Testnamen dürfen präzise englische Bezeichner verwenden.
