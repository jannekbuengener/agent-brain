# Slice 5 — Acceptance / Parity / Risk Matrix

**Issue:** [#9](https://github.com/jannekbuengener/agent-brain/issues/9)  
**Vorgänger:** #6 / Context Package & Briefing  
**Nachfolger:** #16 / Knowledge Build, Seed & Import  
**Status:** vorbereitete Abnahmematrix; Ergebnisse werden erst nach Implementierung eingetragen.

## Warum diese Matrix existiert

Ein grüner Testlauf allein beweist nicht, dass Slice #9 vollständig geliefert ist. Für jedes Acceptance Criterion wird deshalb vorab festgelegt:

- welcher portable Contract entstehen muss,
- welche Claire-Charakterisierung als Vergleich dient,
- welche Agent-Brain-Evidence den Punkt später beweist,
- welche Fehlinterpretation ausdrücklich verhindert werden muss.

## Acceptance Criteria → Evidence

| AC | Anforderung aus #9 | Spätere Agent-Brain-Evidence | Claire-Parity / Referenz | Fail-closed Gegenbeweis |
| --- | --- | --- | --- | --- |
| AC1 | Beliebiges Test-Repo kann als explizites Profil indexiert werden | neutraler Fixture-Repo-Test mit `RepositorySource` + `RepositoryProfile`; End-to-End `build_repository_index()` | `test_context_indexer.py` Fixture-Verhalten | kein Default auf Claire-Root, cwd oder bekannten Workspace |
| AC2 | Claire ist nur Profil/Adapter, kein hardcodierter Canonical Root | Product-Neutrality-Scan auf `src/agent_brain/connectors` + neutrale Fixtures; keine Claire/CDB/Trading-Namen | `context_indexer.py` hardcodierte Defaults als Negativreferenz | kein `Claire_de_Binare`, `CDB_*`, Trading-/LR-/Echtgeld-Wortschatz im generischen Runtime-Code |
| AC3 | Lokale und Remote-Identität bleiben getrennt nachvollziehbar | Inventory-Test mit drei absichtlich abweichenden Werten: lokaler Pfad, konfigurierte `RepositorySource`, observed Git-Origin | `test_cross_repo_root_inventory.py::test_local_and_github_fields_are_separate` | observed Origin darf konfigurierte Source nicht still überschreiben; lokaler Ordnername beweist kein Ownership |
| AC4 | Forbidden-/Sensitivity-Regeln sind konfigurierbar und fail-closed | Policy-/Scanner-Tests für caller-supplied Regeln, Secret-Redaction, Ambiguität und Path-Containment | `context_ingestion_scope.yaml`, `test_context_indexer.py` | unsichere/mehrdeutige Datei erzeugt keinen normalen Artifact-/Index-Record |
| AC5 | Kein Clone/Write als versteckter Seiteneffekt | Tests/Scope-Scan: kein `requests`, kein `gh repo view`, kein clone/fetch/checkout, kein DB-Client; Scanner/Inventory nur read-only | Claire Indexer war offline; Cross-Repo-Inventar hatte optionales `gh`, das bewusst nicht portiert wird | kein Netzwerkzugriff, kein Repo-Write, keine Ausgabe in Source-Repo durch Core-API |
| AC6 | Outputs entsprechen #15 Source-/Index-Verträgen | Type-/Serialization-Tests mit exakt `ArtifactRef`, `IndexRecord`, `GraphEdge` und `RepositorySource` | `test_context_graph_contract.py` plus #15 Agent-Brain-Contracts | keine parallelen `RepoArtifact`-/`GraphRecord`-/Source-Contract-Klassen |
| AC7 | Neutraler Fixture-Repo-Test vorhanden | `tests/fixtures/connectors/repository_neutral/` mit Python, Markdown, Config, Syntaxfehler, Exclude und Forbidden-Fall | Claire Fixture-Repos als Charakterisierung | Fixture enthält keine Claire-/Trading-Semantik und braucht keine externe Runtime |
| AC8 | #16 kann Artefakte deterministisch weiterverarbeiten | stable Ingestion-Fingerprint/Serialization; gleiche Inhalte in anderer Filesystem-Reihenfolge und auf anderem Host ergeben gleiche stabile Identität | wiederholte `run_indexer()`-Charakterisierung in Claire | Wall Clock, absoluter Host-Pfad und Directory-Iteration dürfen Fingerprint nicht verändern |

## Parity Pack für #9

Aus Claire Baseline `84b5e05765fcde402a2565aa37fd42081ee95355` sind vier Testflächen relevant:

| Claire-Test | Was er schützt | Was **nicht** übernommen wird |
| --- | --- | --- |
| `tests/unit/surrealdb/test_context_indexer.py` | Scope, Discovery, Hashing, dry-run/offline Verhalten, robuste Findings | Claire Default-Scope, Output-Write-CLI, SurrealDB-/Live-spezifische Statusfelder |
| `tests/unit/surrealdb/test_context_symbol_extraction.py` | AST-Symbole, Imports, Tests, Config-Refs, Doc-Code-Links, Dependency-Edges | Claire lokale Modulpräfixe als Core-Konstante |
| `tests/unit/tools/mcp/test_cross_repo_root_inventory.py` | required/optional Roots, lokale/Remote-Felder, fail/pass_with_limits | Claire Canonical-Root-Sonderlogik und GitHub-Netzwerkcheck |
| `tests/unit/surrealdb/test_ledger_importer.py` | Event-Reihenfolge, Chain, Hash-/Signatur-Integrität, Redaction | HTTP, Auth, SurrealQL, DB-Duplicate-Preflight und produktive Writes |

**Parity bedeutet hier nicht Dateikopie.** Ein Claire-Test wird nur als Charakterisierung verwendet. Agent Brain erhält neue produktneutrale Tests gegen die eigenen #15-Contracts.

## Kritische Failure Modes

| Priorität | Failure Mode | Erwartetes Verhalten | Geplanter Testowner |
| --- | --- | --- | --- |
| P0 | Symlink/`..`/absolute Path verlässt Repository-Root | fail-closed; Datei niemals lesen | Scanner |
| P0 | Secret/Forbidden Content | kein Klartext in Findings/Records/Fingerprint; normaler Ingestion-Record unterdrückt | Policy + Scanner |
| P0 | lokaler Git-Origin widerspricht konfigurierter Source | beide Werte erhalten; Limitation melden; Source nicht umschreiben | Inventory |
| P0 | Host-Pfad oder Wall Clock beeinflusst stabile Identität | identischer Source-Content bleibt host-/zeitunabhängig | Ingestion + Inventory |
| P1 | Binary/NUL/invalid UTF-8 | deterministisches `limited/skipped`; kein halber ArtifactRef | Scanner |
| P1 | Oversized File | deterministic finding; kein Read über definierte Grenze hinaus | Scanner |
| P1 | Python SyntaxError | Finding für Datei; übriger Repo-Index läuft weiter | Indexer |
| P1 | unbekannter absoluter Import | `unknown`, nicht künstlich `local` | Indexer |
| P1 | fehlendes `.git`/origin/git executable | Local-Inventar bleibt nutzbar; Origin Evidence `LIMITED`, kein Crash | Inventory |
| P1 | Event-Signatur ohne Verifier | Batch fail-closed; keine normalisierten Records aus teilweise akzeptiertem Batch | Ledger |
| P2 | Filesystem liefert andere Iterationsreihenfolge | Records/Edges/Fingerprint identisch sortiert | Scanner + Indexer |
| P2 | gleiche Datei LF vs CRLF | normalisierter Text-Hash stabil | Scanner |

## Security-/Scope-Negative-Controls

Vor Merge müssen mindestens folgende Negativkontrollen belegt sein:

1. kein `requests`/HTTP-/GitHub-Client im Slice-5-Core,
2. kein SurrealQL-/DB-Write-Pfad,
3. kein `git clone`, `fetch`, `checkout`, `reset`, `clean` oder andere Repo-Mutation,
4. keine produktiven Agent-Memory-Writes,
5. keine Claire-/Trading-/LR-/Live-Go-/Echtgeld-Regeln im generischen Connector-Core,
6. keine Secretwerte in serialisierbaren Findings oder Test-Snapshots,
7. keine absoluten Host-Pfade in stabilen IDs/Fingerprints.

## Abnahme-Checkliste nach Implementierung

Die Checkboxes bleiben bewusst offen, bis frische Evidence auf dem finalen PR-Head vorliegt.

- [ ] Alle acht Acceptance Criteria sind mit konkreten Tests/Evidence belegt.
- [ ] Claire-Parity-Fälle wurden verstanden und produktneutral neu abgedeckt.
- [ ] `python -m ruff check .` ist auf dem finalen Head grün.
- [ ] komplette pytest-Suite ist auf Python 3.12/3.13/3.14 in CI grün.
- [ ] Product-Neutrality-/Forbidden-Vocabulary-Regression ist grün.
- [ ] kein Runtime-Dependency-Zuwachs ohne expliziten Scope.
- [ ] Diff enthält ausschließlich #9 + bereits freigegebene Doku.
- [ ] keine offene Review-/Conversation-Finding im Scope.
- [ ] Merge erfolgt nur gegen exakt geprüfte Head-SHA.
- [ ] Merge-SHA liegt live auf `main`.
- [ ] Post-Merge-CI ist grün.
- [ ] Issue #9 ist erst dann `completed`, wenn die Implementation tatsächlich gemergt und live verifiziert ist.

## Übergabe an #16

Slice #16 darf sich nach erfolgreichem #9 auf Folgendes verlassen:

- explizite `RepositorySource`-/`RepositoryProfile`-Identität,
- deterministische `ArtifactRef`-Liste,
- deterministische `IndexRecord`-/`GraphEdge`-Outputs,
- sichere Findings für skipped/forbidden/limited Sources,
- stabilen Ingestion-Fingerprint,
- keine versteckte Persistenz oder DB-Autorität.

#16 muss **nicht** erneut Repository-Discovery, Source-Identität oder statische Extraktion erfinden. Seine Aufgabe beginnt beim reproduzierbaren Knowledge-/Index-Build und kontrollierten Seed/Import.
