# Externe Referenzdokumentation — Agent Brain

**Stand:** 2026-10-20  
**Status:** kanonischer Docs-Index für externe technische Referenzen  
**Quelle:** aus der früheren CDB-Extern-Dokumentationsliste abgeleitet und auf den tatsächlichen Agent-Brain-Scope reduziert.

## Zweck

Diese Datei beantwortet zwei Fragen:

1. **Welche externen Dokumentationen erklären Technologien, die Agent Brain heute tatsächlich benutzt?**
2. **Welche Referenzen werden für bereits geplante Agent-Brain-Slices wahrscheinlich wichtig, ohne heute schon eine Repo-Abhängigkeit zu sein?**

Externe Dokumentation ist **keine Source of Truth für den aktuellen Repo-Zustand**. Bei Widersprüchen gilt weiterhin:

1. GitHub Live
2. Repo Live
3. verifizierte Context-/DB-Evidence
4. kanonische Projektdateien
5. externe Dokumentation

## Status-Legende

| Status | Bedeutung |
|---|---|
| **`ACTIVE`** | Im aktuellen Repository, Build, Test- oder CI-Pfad live belegt. Für gegenwärtige Arbeit besonders relevant. |
| **`NEXT`** | Im kanonischen Agent-Brain-Roadmap-/Extraction-Scope konkret vorgesehen, aber noch keine aktive Runtime-Abhängigkeit. |
| **`REFERENCE`** | Hilfreiche offizielle Referenz für Entwicklung/Operator-Arbeit, aber nicht als Agent-Brain-Dependency belegt. |
| **`PARKED`** | Kein gegenwärtiger Agent-Brain-Scope. Nur bei einem konkreten zukünftigen Issue wieder hochstufen. |

> **Agentenregel:** `ACTIVE` zuerst lesen, wenn die Aufgabe den jeweiligen Bereich berührt. `NEXT` nur für den zugehörigen Roadmap-Slice verwenden. `REFERENCE` und `PARKED` niemals als Beweis dafür behandeln, dass eine Technologie im Repo bereits eingesetzt wird.

---

## Gegenwärtig besonders relevant

Diese Referenzen sind durch den aktuellen Repo-/CI-Stand belegt und deshalb für heutige Änderungen besonders wichtig.

| Status | Priorität | Referenz | Warum aktuell relevant | Repo-Beleg |
|---|---:|---|---|---|
| **`ACTIVE`** | `P0` | [Python](https://docs.python.org/3/) | Primäre Sprache und Runtime-Baseline. | `pyproject.toml` verlangt Python `>=3.12`; CI testet 3.12/3.13/3.14. |
| **`ACTIVE`** | `P0` | [pytest](https://docs.pytest.org/en/stable/) | Test-Framework für Contract-, Foundation- und Extraction-Regressionstests. | `pyproject.toml` dev dependency; `tests/`; CI führt `python -m pytest -q` aus. |
| **`ACTIVE`** | `P0` | [Ruff](https://docs.astral.sh/ruff/) | Aktiver Linter und CI-Gate. | `pyproject.toml`; CI führt `python -m ruff check .` aus. |
| **`ACTIVE`** | `P0` | [Setuptools](https://setuptools.pypa.io/en/latest/) | Aktuelles Build-Backend und src-layout Packaging. | `pyproject.toml`: `setuptools.build_meta`, `setuptools>=75`. |
| **`ACTIVE`** | `P0` | [Python Packaging User Guide](https://packaging.python.org/) | Referenz für editable installs, Build-/Distribution-Grenzen und spätere Versionierung. | `python -m pip install -e ".[dev]"`; Slice #17 ist Distribution/Versionierung. |
| **`ACTIVE`** | `P0` | [GitHub Actions](https://docs.github.com/en/actions) | CI ist gegenwärtig die verbindliche automatische Validierungsfläche. | `.github/workflows/ci.yml`. |
| **`ACTIVE`** | `P1` | [actions/checkout](https://github.com/actions/checkout) | Aktiver CI-Baustein. | `.github/workflows/ci.yml` nutzt `actions/checkout@v7`. |
| **`ACTIVE`** | `P1` | [actions/setup-python](https://github.com/actions/setup-python) | Aktiver Python-Matrix-/Cache-Baustein. | `.github/workflows/ci.yml` nutzt `actions/setup-python@v7`. |
| **`ACTIVE`** | `P0` | [GitHub Docs](https://docs.github.com/) | Issues, PRs, Checks und Repo-Live-State sind Teil der kanonischen Arbeitsweise. | `AGENTS.md` Wahrheitshierarchie und Git-/PR-Regeln. |
| **`ACTIVE`** | `P1` | [Git](https://git-scm.com/docs) | Branch-/Worktree-/Diff- und Merge-Grundlage des Entwicklungsmodells. | `AGENTS.md` verlangt isolierten Branch/Worktree und verbietet direkte Implementierung auf `main`. |

### Was `ACTIVE` ausdrücklich bedeutet

`ACTIVE` ist kein allgemeines Architekturwunschbild. Der Status wird nur vergeben, wenn der aktuelle Repo-Stand die Technologie direkt belegt. Bei einem späteren Austausch der Technologie muss diese Liste zusammen mit dem Repo-State aktualisiert werden.

---

## Konkret nächste / bereits geplante Referenzen

Diese Technologien sind für die Roadmap wichtig, dürfen aber **noch nicht** wie heutige Runtime-Abhängigkeiten behandelt werden.

| Status | Priorität | Referenz | Geplanter Bezug | Aktuelle Grenze |
|---|---:|---|---|---|
| **`NEXT`** | `P0` | [SurrealDB](https://surrealdb.com/docs) | Roadmap-Slice `SurrealDB Read` (#10) und separates State-Migration-Gate #21. | Namespace/Extraction-Grenze existiert, aber noch keine freigegebene SurrealDB-Runtime im Core. |
| **`NEXT`** | `P1` | [Model Context Protocol](https://modelcontextprotocol.io/docs) | Relevant für spätere Protocol-/Consumer-Adapter und Claire-Parity-Kontext. | Der private ChatGPT-MCP ist ausdrücklich **keine** Repo-Abhängigkeit; Core-Tests/CI dürfen ihn nicht voraussetzen. |
| **`NEXT`** | `P1` | [JSON Schema](https://json-schema.org/) | Nützlich für spätere formale Schema-/Protocol-Validierung der versionierten Contracts. | Gegenwärtige Contracts sind Python-Datenverträge; `jsonschema` ist keine Runtime-Dependency. |
| **`NEXT`** | `P1` | [PyPA Version Specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/) | Slice #17 Distribution/Versionierung. | Version `0.0.0` ist aktuell bewusst nur Scaffold-Platzhalter. |

---

## Entwicklungs- und Operator-Referenzen

Nützlich für Agenten und Menschen, aber nicht automatisch Teil des Agent-Brain-Produkts.

| Status | Priorität | Referenz | Verwendung |
|---|---:|---|---|
| **`REFERENCE`** | `P1` | [GitHub CLI](https://cli.github.com/manual/) | Issues/PRs/Checks bei lokalen Operator-Workflows. Nicht als Runtime-Abhängigkeit behandeln. |
| **`REFERENCE`** | `P1` | [OpenAI Codex](https://developers.openai.com/codex) | Hilfreich für AGENTS.md-/Agenten-Workflows, wenn Codex als Worker eingesetzt wird. Tool-spezifische Features sind nicht Repo-Canon. |
| **`REFERENCE`** | `P1` | [Claude Code](https://code.claude.com/docs/en/overview) | Optionaler Coding-Agent/Worker. Keine aktuelle Repo-Dependency. |
| **`REFERENCE`** | `P1` | [Cursor](https://cursor.com/docs) | Optionaler Editor-/Agenten-Workflow. Keine aktuelle Repo-Dependency. |
| **`REFERENCE`** | `P1` | [Gemini API / Google AI](https://ai.google.dev/gemini-api/docs) | Optionaler Agent-/Model-Kontext. Keine aktuelle Repo-Dependency. |
| **`REFERENCE`** | `P1` | [GitHub Copilot](https://docs.github.com/en/copilot) | Optionaler Review-/Coding-Workflow. Keine aktuelle Repo-Dependency. |
| **`REFERENCE`** | `P2` | [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) | Mögliche Commit-/Release-Konvention; derzeit kein eigener verpflichtender Repo-Contract. |

---

## Geparkt — nur bei echtem Agent-Brain-Scope

Die folgende Dokumentation stammt aus dem breiteren CDB-/Tooling-Umfeld oder ist allgemein interessant. Sie wird **nicht** als aktuelle Agent-Brain-Technologie dargestellt.

| Status | Referenz | Warum geparkt |
|---|---|---|
| **`PARKED`** | [Docker](https://docs.docker.com/) / [Docker Compose](https://docs.docker.com/compose/) | Kein aktueller Agent-Brain-Container-/Compose-Pfad. |
| **`PARKED`** | [Dev Containers](https://containers.dev/) | Kein aktueller `.devcontainer`-Pfad. |
| **`PARKED`** | [PostgreSQL](https://www.postgresql.org/docs/) | Kein aktueller Agent-Brain-Postgres-Pfad. |
| **`PARKED`** | [Redis](https://redis.io/docs/latest/) | Kein aktueller Agent-Brain-Redis-Pfad. |
| **`PARKED`** | [Prometheus](https://prometheus.io/docs/) / [Grafana](https://grafana.com/docs/) | Kein aktueller Monitoring-Runtime-Scope im Agent-Brain-Repo. |
| **`PARKED`** | [mypy](https://mypy.readthedocs.io/en/stable/) | Nicht in `pyproject.toml` oder CI aktiviert. |
| **`PARKED`** | [Black](https://black.readthedocs.io/en/stable/) | Nicht in `pyproject.toml` oder CI aktiviert; Ruff ist das aktuelle Lint-Gate. |
| **`PARKED`** | [pre-commit](https://pre-commit.com/) | Keine aktuelle `.pre-commit-config.yaml` im Agent-Brain-Repo. |
| **`PARKED`** | [Gitleaks](https://gitleaks.io/) | Keine aktuelle Gitleaks-Konfiguration im Agent-Brain-Repo. |
| **`PARKED`** | [Bandit](https://bandit.readthedocs.io/en/latest/) | Nicht in aktuellem Dev-/CI-Stack. |
| **`PARKED`** | [pip-audit](https://pypa.github.io/pip-audit/) | Nicht in aktuellem Dev-/CI-Stack. |
| **`PARKED`** | [Trivy](https://trivy.dev/docs/) | Kein aktueller Container-/Supply-Chain-Scan im Repo. |
| **`PARKED`** | [FastAPI](https://fastapi.tiangolo.com/) | Keine aktuelle HTTP-Runtime. |
| **`PARKED`** | [SQLAlchemy](https://docs.sqlalchemy.org/) / [Alembic](https://alembic.sqlalchemy.org/en/latest/) | Keine aktuelle ORM-/Migration-Dependency. |
| **`PARKED`** | [Node.js](https://nodejs.org/docs/latest/api/) / [npm](https://docs.npmjs.com/) | Agent Brain ist gegenwärtig ein Python-Paket; Node ist kein Repo-Core-Pfad. |
| **`PARKED`** | [Kubernetes](https://kubernetes.io/docs/) | Kein aktueller Deployment-Scope. |

---

## Bewusst nicht aus der CDB-Liste übernommen

Die ursprüngliche Liste enthielt produkt- und trading-spezifische Referenzen wie MEXC Spot/Contract APIs, WebSocket-Market-Data, CDB-Monitoring-/Execution-Flächen und weitere Claire-spezifische Runtime-Komponenten.

Diese gehören **nicht** in den kanonischen Agent-Brain-Referenzindex, solange kein eigenständiges Agent-Brain-Issue einen generischen Bezug herstellt. Das verhindert, dass Agenten aus externer Dokumentation fälschlich eine Trading-, Exchange- oder Live-Autorität für Agent Brain ableiten.

## Pflege-Regel

Eine Referenz darf auf `ACTIVE` hochgestuft werden, wenn mindestens eines gilt:

1. Die Technologie ist direkte Runtime- oder Dev-Dependency in `pyproject.toml` oder einer gleichwertigen kanonischen Manifestdatei.
2. Sie wird durch aktuelle CI-/Build-Konfiguration ausgeführt.
3. Ein produktiver Modulpfad importiert oder verwendet sie direkt.
4. Ein kanonischer Repo-Contract erklärt sie ausdrücklich als gegenwärtige technische Baseline.

`NEXT` setzt einen konkreten Roadmap-/Issue-/Extraction-Bezug voraus. Reine Ideen bleiben `REFERENCE` oder `PARKED`.

## Agenten-Leseregel

Bei einer Aufgabe mit externer Technologie:

1. zuerst GitHub-/Repo-Live-State und das aktuelle Issue lesen,
2. danach den passenden `ACTIVE`- oder `NEXT`-Eintrag hier auswählen,
3. bevorzugt offizielle Upstream-Dokumentation verwenden,
4. externe Docs nur zur Erklärung der eingesetzten Technologie nutzen — niemals zum Überschreiben des aktuellen Repo-Contracts.
