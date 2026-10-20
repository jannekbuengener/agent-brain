# Repository Ingestion und Connectors

Slice #9 besitzt den produktneutralen, read-only und offline Repository-Ingestionskern. Er liest explizit profilierte lokale Repositories und erzeugt deterministische #15-Verträge (`RepositorySource`, `RepositoryProfile`, `ArtifactRef`, `IndexRecord`, `GraphEdge`) als Eingabe für den Knowledge-Build #16.

## Module

| Modul | Verantwortung |
|---|---|
| `agent_brain.connectors.ingestion` | Produktneutrale Policy-/Result-Verträge (`IngestionPolicy`, `SensitivityRule`, `ForbiddenRule`, `IngestionFinding`, `RepositoryIngestionResult`) und deterministischer Ingestion-Fingerprint. |
| `agent_brain.connectors.inventory` | Lokales, read-only Repository-/Workspace-Inventar. Lokaler Pfad, konfigurierte Source-Identität und beobachteter Git-Origin bleiben getrennte Evidence-Felder. |
| `agent_brain.connectors.scanner` | Sichere, lokale Dateientdeckung. Include/Exclude, Dateitypen, LF/CRLF-Normalisierung, Größenlimit, Binary, invalid UTF-8, Forbidden-/Sensitivity-Regeln und Path-/Symlink-Containment. |
| `agent_brain.connectors.indexer` | Statische Python-/Markdown-/Config-Extraktion über `ast`, `json` und `tomllib` in `IndexRecord`/`GraphEdge`. Kein Import von Zielcode, kein YAML-Parser. |
| `agent_brain.connectors.ledger` | Portable Event-Normalisierung mit Batch-Preflight, Integritätsprüfung, Redaction und per-Agent Previous-Event-Chain. Kein DB-Transport. |

## Determinismus und Sicherheit

- IDs und Fingerprints sind unabhängig von Dateisystem-Iteration, absolutem Host-Pfad und Wall Clock.
- Text wird vor dem Hashing auf `\n` normalisiert; Binary und invalid UTF-8 werden nie still als Text indexiert.
- Symlink-, `..`- und absolute Escapes aus dem expliziten Repository-Root werden fail-closed ausgeschlossen und nie gelesen.
- Forbidden-/Sensitivity-Regeln sind caller-supplied und fail-closed; kein Secret-Klartext erreicht Findings, Records oder Fingerprints.
- Python-Syntaxfehler erzeugen eine Finding, während der Rest des Repositories deterministisch weiter indexiert wird.
- Unbekannte absolute Imports bleiben `unknown`; nur `IngestionPolicy.local_module_prefixes` und relative Imports klassifizieren als `local`.

## Ownership-Grenzen

Slice #9 **liest lokale Repositories und erzeugt portable Verträge**. Er übernimmt keine Verantwortung späterer Slices:

- #16 Knowledge Build / Seed / Import besitzt reproduzierbaren Build und kontrolliertes Persistieren.
- #7 Retrieval berechnet später relevante Kontexte.
- #10 SurrealDB Read führt Datenbank-Lesezugriff ein.
- #13 Claire Adapter / Consumer Cutover bindet Claire-spezifische Profile an.
- #18 Parity / Dual Run vergleicht später gegen die Claire-Baseline.
- #21 State Migration Gate schützt echten SurrealDB-primary State.

Nicht Teil dieses Slices sind DB-Writes, Seed/Import, HTTP-/GitHub-Netzwerkzugriff, Clone/Fetch/Checkout/Reset, produktive Agent-Memory-Writes, Workforce-Routing, SurrealDB-Runtime, YAML-Ledger-Parsing oder Claire-/Trading-/LR-/Live-Go-/Echtgeld-Regeln.

## Identitätsregel

Diese Ebenen bleiben getrennt:

```text
local_path
configured_repository_identity / source_uri
observed_git_origin
revision
```

Ein Mismatch wird als Evidence/Limitation berichtet und darf die konfigurierte `RepositorySource` nicht still umschreiben. Ein lokaler Ordnername oder seine Workspace-Position beweist keine Remote-Ownership.

## Parity-Mapping zur gepinnten Extraktionsbaseline

Die produktneutralen Regressionen charakterisieren die portable Semantik der gepinnten Claire-Baseline `84b5e05765fcde402a2565aa37fd42081ee95355`:

| Claire-Baseline | Agent-Brain-Regression |
|---|---|
| `test_context_indexer.py` | `tests/connectors/test_scanner.py`, `tests/connectors/test_indexer.py` |
| `test_context_symbol_extraction.py` | `tests/connectors/test_indexer.py` |
| `test_cross_repo_root_inventory.py` | `tests/connectors/test_inventory.py` |
| `test_ledger_importer.py` | `tests/connectors/test_ledger.py` |

Claire-spezifische Default-Scopes, lokale Modulpräfixe als Core-Konstante, SurrealQL-, HTTP-, Auth-, DB-Preflight- und produktive Write-Verhalten werden nicht in den generischen Core übernommen. Details stehen in `docs/extraction/SLICE_5_ACCEPTANCE_PARITY_MATRIX.md`.

## Öffentliche API

Der stabile Slice-5-Einstieg ist `agent_brain.connectors`. Die package-level Exports werden durch `tests/connectors/test_connector_public_surface.py` geschützt. Produktneutralität und Scope werden durch `tests/connectors/test_connector_product_neutrality.py` und `tests/connectors/test_scope_guards.py` geschützt.

## Externe technische Referenzen

Bei Dependency-, CI-, Protocol-, DB- oder Tooling-Fragen zusätzlich [Externe Referenzdokumentation](../external-docs/index.md) lesen. `P0`/`P1` bedeuten dort aktuell durch Repo-Evidence belegte Kern-/Sekundärreferenzen; `P2` ist geparkt/reference-only und keine Aussage über vorhandene Runtime-Fähigkeiten oder Dependencies.
