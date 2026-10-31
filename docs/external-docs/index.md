# Externe Referenzdokumentation — Agent Brain

**Stand:** 2026-10-20  
**Status:** kanonischer Docs-Index für externe technische Referenzen  
**Contract:** <https://github.com/jannekbuengener/agent-workforce/blob/main/contracts/EXTERNAL_REFERENCE_CONTRACT.md>

## Zweck

Diese Datei dokumentiert, welche externen technischen Referenzen für den **aktuellen Agent-Brain-Repozustand** relevant sind und welche Quellen bewusst nur für spätere Slices geparkt bleiben.

Externe Dokumentation ist keine Source of Truth für den aktuellen Repo-Zustand. Bei Widersprüchen gilt weiterhin:

1. GitHub Live
2. Repo Live
3. verifizierte Context-/DB-Evidence
4. kanonische Projektdateien
5. externe Dokumentation

## Priorität und Source Authority

- `P0` — aktive Kernreferenz, durch aktuelle Repo-/Build-/Test-/CI-Evidence belegt.
- `P1` — aktive sekundäre Referenz, ebenfalls durch aktuelle Repo-Evidence belegt.
- `P2` — geparkt/reference-only; darf nicht als vorhandene Runtime-Fähigkeit oder Dependency interpretiert werden.

Priorität beschreibt Repo-Relevanz, nicht Wahrheit. External Source Authority ist separat:

`OFFICIAL_SPEC` > `OFFICIAL_DOCS` > `UPSTREAM_PROJECT_DOCS` > `UPSTREAM_ISSUES_RELEASES` > `ESTABLISHED_TECHNICAL_KNOWLEDGE` > `COMMUNITY` > `EXAMPLE_DISCOVERY`.

## Aktive Referenzen

| Kategorie | Referenz | Priorität | Source type | Authority | Warum aktuell relevant | Repo-Beleg / Wann nutzen |
|---|---|---|---|---|---|---|
| Runtime | [Python](https://docs.python.org/3/) | `P0` | `official_docs` | `OFFICIAL_DOCS` | Primäre Sprache und Runtime-Baseline. | `pyproject.toml` verlangt Python `>=3.12`; bei Runtime-/Stdlib-/Kompatibilitätsfragen. |
| Testing | [pytest](https://docs.pytest.org/en/stable/) | `P0` | `official_docs` | `OFFICIAL_DOCS` | Contract-, Foundation- und Extraction-Regressionstests. | `pyproject.toml` dev dependency, `tests/`, `python -m pytest -q`. |
| Static analysis | [Ruff](https://docs.astral.sh/ruff/) | `P0` | `official_docs` | `OFFICIAL_DOCS` | Aktiver Linter und Validierungspfad. | `pyproject.toml`, `python -m ruff check .`. |
| Packaging | [Setuptools](https://setuptools.pypa.io/en/latest/) | `P0` | `official_docs` | `OFFICIAL_DOCS` | Aktuelles Build-Backend und src-layout Packaging. | `pyproject.toml`: `setuptools.build_meta`, `setuptools>=75`. |
| Repo/CI | [GitHub Actions](https://docs.github.com/en/actions) | `P0` | `official_docs` | `OFFICIAL_DOCS` | Automatische Validierungsfläche. | `.github/workflows/ci.yml`; bei CI-/Check-Änderungen. |
| Repo/SCM | [GitHub Docs](https://docs.github.com/) | `P0` | `official_docs` | `OFFICIAL_DOCS` | Issues, PRs, Checks und GitHub-Live-State sind Teil der kanonischen Arbeitsweise. | `AGENTS.md` Wahrheitshierarchie und Git-/PR-Regeln. |
| Packaging | [Python Packaging User Guide](https://packaging.python.org/) | `P1` | `official_docs` | `OFFICIAL_DOCS` | Editable installs und Packaging-/Distribution-Grenzen. | `python -m pip install -e ".[dev]"`; bei Packaging-/Distribution-Arbeit. |
| Repo/CI | [actions/checkout](https://github.com/actions/checkout) | `P1` | `upstream_project_docs` | `UPSTREAM_PROJECT_DOCS` | Aktiver CI-Baustein. | `.github/workflows/ci.yml` nutzt `actions/checkout@v7`. |
| Repo/CI | [actions/setup-python](https://github.com/actions/setup-python) | `P1` | `upstream_project_docs` | `UPSTREAM_PROJECT_DOCS` | Aktiver Python-Matrix-/Cache-Baustein. | `.github/workflows/ci.yml` nutzt `actions/setup-python@v7`. |
| Repo/SCM | [Git](https://git-scm.com/docs) | `P1` | `official_docs` | `OFFICIAL_DOCS` | Branch-/Worktree-/Diff-/Merge-Grundlage. | `AGENTS.md` verlangt isolierten Branch/Worktree und verbietet direkte Implementierung auf `main`. |

## Geparkte / geplante Referenzen

Die folgenden Quellen haben einen dokumentierten möglichen Bezug, sind aber **keine aktuelle Runtime- oder Dependency-Evidence** und bleiben deshalb `P2`.

| Referenz | Priorität | Source type | Authority | Geplanter / referenzieller Bezug | Aktuelle Grenze |
|---|---|---|---|---|---|
| [SurrealDB](https://surrealdb.com/docs) | `P2` | `official_docs` | `OFFICIAL_DOCS` | Roadmap-Slice `SurrealDB Read` (#10), Knowledge Build (#16) und separates State-Migration-Gate #21. | Keine freigegebene SurrealDB-Runtime im aktuellen Core; Namespace und Research allein sind keine Capability. |
| [Model Context Protocol](https://modelcontextprotocol.io/docs) | `P2` | `official_docs` | `OFFICIAL_DOCS` | Spätere Protocol-/Consumer-Adapter können MCP-relevant werden. | Privater ChatGPT-MCP ist ausdrücklich keine Repo-Abhängigkeit; Tests/CI dürfen ihn nicht voraussetzen. |
| [JSON Schema](https://json-schema.org/) | `P2` | `official_spec` | `OFFICIAL_SPEC` | Mögliche spätere formale Schema-/Protocol-Validierung. | Aktuelle Contracts sind Python-Datenverträge; keine jsonschema-Runtime-Dependency. |
| [PyPA Version Specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/) | `P1` | `official_spec` | `OFFICIAL_SPEC` | Distribution-/Versionierungs-Slice #17. | `pyproject.toml` Version + `agent_brain.distribution` Pin-/Compat-Contract; siehe `docs/distribution/`. |
| [GitHub CLI](https://cli.github.com/manual/) | `P2` | `official_docs` | `OFFICIAL_DOCS` | Optionale Operator-Referenz für Issues/PRs/Checks. | Keine Agent-Brain-Runtime-Dependency. |
| [OpenAI Codex](https://developers.openai.com/codex) | `P2` | `official_docs` | `OFFICIAL_DOCS` | Optionaler Coding-Agent/Worker. | Tool-spezifische Features sind kein Repo-Canon. |
| [Claude Code](https://code.claude.com/docs/en/overview) | `P2` | `official_docs` | `OFFICIAL_DOCS` | Optionaler Coding-Agent/Worker. | Keine Repo-Dependency. |
| [Cursor](https://cursor.com/docs) | `P2` | `official_docs` | `OFFICIAL_DOCS` | Optionaler Editor-/Agenten-Workflow. | Keine Repo-Dependency. |
| [Gemini API / Google AI](https://ai.google.dev/gemini-api/docs) | `P2` | `official_docs` | `OFFICIAL_DOCS` | Optionaler Agent-/Model-Kontext. | Keine Repo-Dependency. |
| [GitHub Copilot](https://docs.github.com/en/copilot) | `P2` | `official_docs` | `OFFICIAL_DOCS` | Optionaler Review-/Coding-Workflow. | Keine Repo-Dependency. |
| [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) | `P2` | `official_spec` | `OFFICIAL_SPEC` | Mögliche Commit-/Release-Konvention. | Kein verpflichtender Repo-Contract. |

### SurrealDB Research-Landschaft

Für SurrealDB-nahe Arbeit existiert die lokale [SurrealDB Reference Landscape](surrealdb-reference-landscape.md). Sie ist ein kuratiertes Reuse-/Research-Artefakt und **keine Runtime-Dependency**. Für #9 darf daraus keine SurrealDB-Abhängigkeit entstehen; für #10/#16/#21 kann sie Kandidaten und Upstream-Pfade liefern. Vor Übernahme müssen offizieller Upstream und aktuelle Dokumentation erneut geprüft werden.

### Nicht aktueller Agent-Brain-Scope

Docker/Compose, Dev Containers, PostgreSQL, Redis, Prometheus/Grafana, mypy, Black, pre-commit, Gitleaks, Bandit, pip-audit, Trivy, FastAPI, SQLAlchemy/Alembic, Node/npm und Kubernetes sind gegenwärtig **nicht** als Agent-Brain-Technologie belegt. Sie werden nicht einzeln im aktiven Index geführt; bei einem konkreten zukünftigen Issue können sie als `P2` mit dokumentiertem Zweck aufgenommen werden.

Produkt- und trading-spezifische CDB-Referenzen wie MEXC-, Market-Data-, Execution- oder CDB-Monitoring-Flächen gehören nicht in diesen Index, solange kein eigenständiger produktneutraler Agent-Brain-Scope existiert.

## Pflege-Regel

Eine Referenz darf auf `P0` oder `P1` hochgestuft werden, wenn mindestens eines gilt:

1. Die Technologie ist direkte Runtime- oder Dev-Dependency in `pyproject.toml` oder einer gleichwertigen kanonischen Manifestdatei.
2. Sie wird durch aktuelle CI-/Build-Konfiguration ausgeführt.
3. Ein produktiver Modulpfad importiert oder verwendet sie direkt.
4. Ein kanonischer Repo-Contract erklärt sie ausdrücklich als gegenwärtige technische Baseline.

Ein geplanter Slice, optionaler Worker oder allgemeines Interesse reicht nur für `P2`, nicht für eine aktive Einstufung.

## Agenten-Leseregel

Bei einer Aufgabe mit externer Technologie:

1. zuerst GitHub-/Repo-Live-State und das aktuelle Issue lesen,
2. danach nur passende `P0`/`P1`-Einträge laden,
3. `P2` nur verwenden, wenn der aktuelle Task den dokumentierten zukünftigen/reference Scope tatsächlich aktiviert,
4. bei SurrealDB-naher Arbeit zusätzlich die [SurrealDB Reference Landscape](surrealdb-reference-landscape.md) lesen,
5. bevorzugt offizielle/upstream Dokumentation verwenden,
6. externe oder lokale Reference-Repos niemals zum Überschreiben des aktuellen Agent-Brain-Contracts oder zum Erfinden einer Runtime-Fähigkeit verwenden.

Keine workstation-spezifischen absoluten Pfade, Credentials, privaten Endpoints oder CDB-/Produktdaten in diesem Index pflegen.