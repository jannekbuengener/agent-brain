# Slice 5 — Source → Target Matrix

**Issue:** [#9 — Repository Ingestion und Connectors generalisieren](https://github.com/jannekbuengener/agent-brain/issues/9)  
**Claire baseline:** `jannekbuengener/Claire_de_Binare@84b5e05765fcde402a2565aa37fd42081ee95355`  
**Agent-Brain baseline vor Slice 5:** `ad2067872e8af687f506a9c82b4b81b13e627e2b`  
**Status:** `READY_FOR_IMPLEMENTATION` — Architektur und Ownership sind geklärt; dieses Dokument autorisiert noch keine Produktcode-Änderung.

## Zweck

Diese Matrix verhindert eine Blindkopie der Claire-Implementierung. Sie legt für jede relevante Quelle fest:

1. welches Verhalten tatsächlich wiederverwendbar ist,
2. welche Claire-Kopplung entfernt werden muss,
3. welches Agent-Brain-Zielmodul den generischen Contract besitzt,
4. was ausdrücklich in Claire oder einem späteren Slice bleibt.

Grundregel: **Extraktion statt Rewrite, aber Verhalten statt Dateikopie.**

## Zielgrenzen in Agent Brain

| Ziel | Verantwortung in #9 | Nicht Teil von #9 |
| --- | --- | --- |
| `agent_brain.connectors.ingestion` | produktneutrale Ingestion-Policy, Findings, deterministischer Ergebnis-/Fingerprint-Contract | Filesystem-I/O, DB, CLI |
| `agent_brain.connectors.inventory` | lokales Repo-/Workspace-Inventar; lokale Identität und konfigurierte/observed Remote-Identität getrennt | GitHub-Reachability, Clone, Fetch |
| `agent_brain.connectors.scanner` | sichere lokale Dateidiscovery, Include/Exclude, File-Type, Size, UTF-8, Sensitivity/Forbidden | Knowledge-Build, Persistenz |
| `agent_brain.connectors.indexer` | statische Python-/Markdown-/Config-Extraktion in #15 `IndexRecord`/`GraphEdge` | Retrieval, Ranking, DB-Abfragen |
| `agent_brain.connectors.ledger` | portable Event-Normalisierung und Integritätsprüfung aus caller-supplied Daten | YAML-Loader, HTTP, SurrealQL, DB-Dedupe/Write |

## Claire → Agent Brain

### 1. `tools/surrealdb/context_indexer.py`

**Claire-Rolle:** offline Context Indexer mit Scope-Config, Dateidiscovery, Hashing, Markdown-/Python-/Config-Extraktion, JSONL-Export und CLI-Flächen.

| Claire-Verhalten | Entscheidung | Agent-Brain-Ziel | Begründung / Änderung |
| --- | --- | --- | --- |
| `run_indexer()` als Offline-Orchestrierung | `ADAPTER → MOVE` | `scanner.py` + `indexer.py` | Prinzip übernehmen; kein Claire-Default-Root und keine Claire-Config als impliziter Canon. |
| stabile Artefakt-/Record-IDs und normalisierte Hashes | `MOVE` | `ingestion.py` / `scanner.py` | Auf vorhandene `canonical_hash`- und #15-Contracts ausrichten. |
| Include-/Exclude-Regeln | `ADAPTER → MOVE` | `RepositoryProfile` + `IngestionPolicy` | Repo-spezifische Pfade werden Profileingabe statt Core-Konstante. |
| File-Type-Erkennung | `MOVE` | `scanner.py` | Kleine produktneutrale Standardmenge; keine produktbezogene Typsemantik. |
| Secret-/Sensitivity-/Forbidden-Erkennung | `ADAPTER → MOVE` | `ingestion.py` + `scanner.py` | Regeln caller-supplied; generische Redaction aus Foundation wiederverwenden. |
| Markdown-Seiten/Sections/Chunks | `MOVE` | `indexer.py` | Auf `IndexRecord`/`GraphEdge` normalisieren; keine parallelen Contract-Typen. |
| Python-AST-Symbole, Imports, Tests | `MOVE` | `indexer.py` | Portable statische Analyse erhalten. |
| Config-Reference-Extraktion | `MOVE` | `indexer.py` | TOML/JSON dependency-frei; sensitive Werte nur redigiert/gehasht. |
| Doc→Code-Links / Dependency-Edges | `MOVE` | `indexer.py` | generische `references`/`imports`/`contains`/`tests`-Edges. |
| `KNOWN_LOCAL_MODULE_PREFIXES = {core, services, tools, ...}` | `ADAPTER` | `IngestionPolicy.local_module_prefixes` | Keine Claire-Modulnamen im Core. Relative Imports bleiben syntaktisch lokal. |
| `TRADING_STATE_PATH_PARTS` | `STAY / PROFILE` | Claire-Profil später | Agent Brain kennt keine Trading-Domäne. Generischer Core erhält nur konfigurierbare Forbidden-Regeln. |
| `core.utils.clock` / Wall-Clock-Run-ID | `DROP/REPLACE` | Foundation Clock / deterministische Fingerprints | Wall Clock darf Output-Identität nicht beeinflussen. |
| Claire `DEFAULT_SCOPE_CONFIG` | `STAY / ADAPTER` | expliziter `RepositoryProfile`-Input | Kein impliziter Claire-Root oder Claire-Config-Pfad. |
| YAML-Scope-Loader | `DEFER/ADAPTER` | nicht im dependency-freien Core | #9 benötigt keine neue YAML-Runtime-Dependency. |
| CLI `scan/plan/snapshot/validate`, Output-Write-Flächen | `DEFER` | Slice #12 / #16 | Core bleibt API-first; Knowledge-Build/CLI sind getrennte Slices. |
| SurrealDB-/Runtime-Statusfelder im CLI-Output | `DROP` | — | #9 ist DB-unabhängig; keine Fake-DB-Autorität im Output. |

**Parity-Quelle:** `tests/unit/surrealdb/test_context_indexer.py` und `tests/unit/surrealdb/test_context_symbol_extraction.py`.

### 2. `tools/mcp/cross_repo_root_inventory.py`

**Claire-Rolle:** deterministisches Cross-Repo-Inventar für bekannte Claire-Roots und optionale GitHub-Ziele.

| Claire-Verhalten | Entscheidung | Agent-Brain-Ziel | Begründung / Änderung |
| --- | --- | --- | --- |
| required/optional lokale Roots | `MOVE` | `inventory.py` | generische `RepositoryInventorySpec` statt Claire-Root-Katalog. |
| lokale Status `OK/MISSING/LIMITED` | `MOVE` | `inventory.py` | sinnvolle fail-closed Semantik erhalten. |
| `pass/pass_with_limits/fail` | `MOVE` | `inventory.py` | deterministischer Report-Contract. |
| lokales `git remote get-url origin` | `MOVE` | `inventory.py` | read-only lokale Evidence; kein Fetch. |
| konfigurierte GitHub-Identität vs observed Origin | `MOVE + HARDEN` | `inventory.py` | Werte separat halten; Mismatch ist Limitation, kein automatisches Rewrite der Source. |
| Claire als `repo_root`/canonical slug | `ADAPTER/STAY` | Consumer-Profil | Kein Repository ist im generischen Core automatisch canonical. |
| `same_as_canonical`-Sonderlogik | `DROP` | — | Remote-Identität wird explizit im `RepositorySource` angegeben. |
| `CDB_WORKSPACES_REPOS_*` Environment | `STAY` | Consumer/Operator | keine CDB-Env-Namen im Core. |
| `gh repo view` Reachability | `DEFER` | optionaler späterer Connector/Operator | #9 macht keinen Netzwerkzugriff und behauptet keine Remote-Reachability. |
| Wall-Clock Timestamp im Report | `DROP aus Fingerprint` | `inventory.py` | beobachtbarer Display-Wert darf niemals deterministische Identität bestimmen. |

**Parity-Quelle:** `tests/unit/tools/mcp/test_cross_repo_root_inventory.py`.

### 3. `infrastructure/config/surrealdb/context_ingestion_scope.yaml`

**Claire-Rolle:** maschinenlesbarer, dry-run-first Ingestion-Scope mit Include/Conditional/Exclude, Dateitypen, Sensitivity, Forbidden-Patterns, Limits und Guardrails.

| Claire-Konzept | Entscheidung | Agent-Brain-Ziel |
| --- | --- | --- |
| `include_paths`, `exclude_paths`, `allowed_file_types` | `MOVE` | bereits vorhandenes `RepositoryProfile` aus #15 |
| Sensitivity-Klassen / Regeln | `ADAPTER → MOVE` | `IngestionPolicy` |
| Forbidden-Patterns | `ADAPTER → MOVE` | `IngestionPolicy` |
| File-Size/Binary-Grenzen | `MOVE` | `IngestionPolicy` + Scanner |
| repo-relative Pfade / fail-closed Ambiguität | `MOVE` | Scanner-Sicherheitscontract |
| Claire konkrete Pfade (`knowledge/`, `tools/surrealdb/`, etc.) | `STAY / PROFILE` | Claire-Adapter, nicht Core |
| Trading-/Broker-/Risk-/Execution-Ausschlüsse | `STAY / PROFILE` | Claire-Policy, nicht Core |
| LR-/Echtgeld-/Board-Semantik | `STAY` | Claire Governance |
| Output-Roots / Apply-Regeln | `DEFER` | #16/#12 |

Wichtig: Der generische Core kopiert **nicht** die vier Claire-Sensitivity-Klassennamen als zwingenden Universalstandard. Er muss beliebige explizite caller-supplied Klassifikationen tragen können; `forbidden` bleibt als fail-closed Ergebnissemantik relevant.

### 4. `tools/surrealdb/ledger_importer.py`

**Claire-Rolle:** Event-Dateien laden, normalisieren, Integrität prüfen und anschließend append-only nach SurrealDB schreiben.

| Claire-Verhalten | Entscheidung | Agent-Brain-Ziel | Begründung / Änderung |
| --- | --- | --- | --- |
| deterministische Reihenfolge Timestamp + Event-ID | `MOVE` | `ledger.py` | produktneutral. |
| deterministische Fallback-ID | `MOVE` | `ledger.py` | über Foundation Canonical Hashing. |
| per-agent `prev_event_id`-Kette | `MOVE` | `ledger.py` | reine Datenbeziehung, keine Autorität. |
| Evidence-Redaction | `MOVE` | `ledger.py` | vorhandene Foundation-Redaction wiederverwenden. |
| deklarierter Hash vs canonical payload hash | `MOVE` | `ledger.py` | fail-closed Integritätsprüfung. |
| Signatur vorhanden, aber kein Verifier | `MOVE` | `ledger.py` | fail-closed; keine Signatur vortäuschen. |
| YAML-Parsing | `DEFER/ADAPTER` | außerhalb Core | kein PyYAML-Zwang für #9. Caller liefert strukturierte Events. |
| `requests`, URL/Auth/Namespace/Database | `STAY/DEFER` | #10/#16 falls später nötig | DB-/Transport-Scope. |
| SELECT-Duplicate-Preflight | `DEFER` | Persistenzschicht | betrifft Ziel-DB, nicht Source-Normalisierung. |
| `CREATE ... CONTENT`, Transaction, Duplicate DB Handling | `DEFER` | #16 / eigener Adapter | #9 darf keine DB-Befüllung einführen. |

**Parity-Quelle:** `tests/unit/surrealdb/test_ledger_importer.py` — nur die portablen Normalisierungs-/Integritätsfälle, nicht die SurrealDB-Write-Tests.

## Bestehende Agent-Brain-Contracts, die nicht neu erfunden werden dürfen

| Contract | Schema | Rolle in #9 |
| --- | --- | --- |
| `RepositorySource` | `repository-source/v1` | konfigurierte stabile Source-Identität |
| `RepositoryProfile` | `repository-profile/v1` | explizite Repo-Ingestion-Grenze |
| `ArtifactRef` | `artifact-ref/v1` | Source-Pfad + Content-Provenance |
| `IndexRecord` | `index-record/v1` | standardisierter Index-Output |
| `GraphEdge` | `graph-edge/v1` | standardisierte Struktur-/Beziehungsedge |

Keine Slice-5-Komponente darf konkurrierende `RepoArtifact`, `SourceRef`, `GraphRecord` oder Evidence-Typen als zweite Contract-Schicht etablieren.

## Harte Nicht-Übernahmen

Folgendes darf durch #9 **nicht** aus Claire in den generischen Core rutschen:

- Claire als impliziter Canonical Root,
- CDB-/Claire Environment-Namen,
- Trading-/Risk-/Execution-Domänenbegriffe als Core-Regeln,
- Live-Readiness-/Echtgeld-Autorität,
- `gh`/HTTP-Netzwerkzugriff als versteckter Inventarschritt,
- Repository Clone/Checkout/Mutation,
- SurrealDB-Verbindung oder -Write,
- produktive Agent-Memory-Writes,
- CLI-/Operator-Autorität,
- absolute Host-Pfade in stabilen IDs/Fingerprints.

## Reuse-Regel

Vor Eigenbau gilt für jede Implementierungsaufgabe:

1. Claire-Baseline und zugeordneten Parity-Test lesen.
2. vorhandenen Agent-Brain-Contract aus #15/#5 wiederverwenden.
3. bei externer Technologie zuerst vorhandene offizielle/Upstream-Referenz prüfen.
4. nur das portable Verhalten übernehmen.
5. alles Produkt-, Transport-, Persistenz- oder Operator-spezifische explizit `ADAPTER`, `STAY` oder `DEFER` lassen.

Damit ist vor Codebeginn klar, **was kopiert werden darf, was generalisiert werden muss und was ausdrücklich nicht in Agent Brain gehört**.
