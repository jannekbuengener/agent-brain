# Shared Source / Index / Evidence Contracts Implementation Plan

> **For agentic workers:** implementation was executed natively with Superpowers TDD and verification gates.

**Goal:** Slice #15 kanonisiert gemeinsame, produktneutrale Source-, Repository-, Index-/Graph- und Evidence-/Claim-Contracts, auf denen Context Package, Ingestion, Retrieval und Evidence Resolution gemeinsam aufbauen.

**Architecture:** Die stabilen Datentypen leben unter `agent_brain.contracts` und verwenden die Portable Foundation aus `agent_brain.core` für Canonical JSON/Hashing. Jeder Contract besitzt ein explizites `schema_version`-Feld. Additive Felder bleiben innerhalb derselben Major-Version lesbar; Breaking Changes benötigen eine neue Major-Version. Claire-spezifische Source-Namen, Trust-Scoring, Resolver-Logik, Required Reads, SurrealDB-Runtime und Trading-Policy bleiben außerhalb dieses Slices.

**Tech Stack:** Python >=3.12, Standardbibliothek, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-20-agent-brain-extraction-design.md` + Issue #15 + `docs/extraction/SLICE_0_EXTRACTION_CANON.md`

## Global Constraints

- Keine Imports aus `Claire_de_Binare`, `tools.surrealdb` oder Claire-`core.*`.
- Keine Repo-Ingestion, kein Retrieval, kein Context Package, kein Evidence Scoring/Resolver und keine SurrealDB-Runtime.
- Keine Claire-/CDB-/Trading-/LR-/Echtgeld-Namen oder Env-Variablen in generischen Contracts oder neutralen Fixtures.
- Produktive Agent-Memory-Writes bleiben `DEFER`.
- Keine neuen Runtime-Dependencies.
- Contracts sind frozen/immutable, deterministisch serialisierbar und explizit versioniert.
- Unbekannte additive Felder derselben Major-Version werden beim Lesen ignoriert; andere Contract-Familien oder Major-Versionen werden fail-closed abgelehnt.
- Falsche primitive Feldtypen und nicht-kanonische Schema-Strings werden nicht still coercet oder normalisiert.
- `EvidenceRef` und `ClaimRef` bleiben reine Referenz-/Datenverträge. Trust, Resolver und Scoring gehören in Slice #8.

## Completed Tasks

### Task 1 — Contract-Versionierung und Serialisierungsbasis

- [x] `src/agent_brain/contracts/__init__.py`, `versioning.py`, `serialization.py` erstellt.
- [x] RED-Charakterisierung für fehlendes Contract-Paket, malformed/blank versions, falsche Familie und Major-Version ausgeführt.
- [x] `ContractVersion`, `require_compatible_version` und Canonical-JSON-Serialisierung implementiert.
- [x] Fokus-Tests + Ruff GREEN.

### Task 2 — RepositorySource, RepositoryProfile und ArtifactRef

- [x] `repository.py` plus neutrale Repository-Profile-Fixture implementiert.
- [x] Round-Trip-, Additive-v1- und Pflichtfeld-Tests test-first erstellt.
- [x] Scalar-String-Sequenzen in Profile-Pfaden werden fail-closed abgelehnt.
- [x] Keine Filesystem-/Repository-Discovery-Logik vorgezogen.

### Task 3 — Minimal Index-/Graph-Record-Contracts

- [x] `IndexRecord`, `GraphEdge` und deterministischer `graph_fingerprint` implementiert.
- [x] Portable Claire-Erwartungen zu IDs, Source-Refs und Fingerprint-Stabilität charakterisiert.
- [x] Reorder-Stabilität, Strukturänderungen, Pflichtfelder und Confidence-Grenzen getestet.
- [x] Duplicate-/Orphan-/Stale-Link-Analyse bewusst nicht in diesen Basistyp-Layer gezogen.

### Task 4 — EvidenceRef und ClaimRef

- [x] `EvidenceRef` / `ClaimRef` plus neutrale Fixture implementiert.
- [x] Canonical Round-Trips und leere optionale Relationen getestet.
- [x] Zusätzliche Trust-/DB-/Resolver-Metadaten werden als unbekannte additive Daten ignoriert und erzeugen keine Autorität.
- [x] Claire-spezifische Trust-Klassifikationen, Resolver, Scoring und Tool-Namen bleiben draußen.

### Task 5 — Registry, Producer-/Consumer-Richtung und Kompatibilität

- [x] Statische `CONTRACT_SCHEMAS` Registry implementiert.
- [x] `docs/contracts/README.md` mit Contract-Familien, Producer-/Consumer-Richtung und v1-Kompatibilitätsregeln erstellt.
- [x] README, `START_HIER` und `DEVELOPMENT` auf `SLICE_3_SHARED_CONTRACTS` aktualisiert.
- [x] #6 als nächsten linearen Slice dokumentiert.

### Task 6 — Final Scope-/Parity-Audit

- [x] Claire-Parity-Gates `test_context_graph_contract.py`, `test_db_record_evidence_contract.py` und `test_wave14_context_record_schemas.py` den neuen neutralen Tests zugeordnet; Trust/Resolver/Runtime bleibt deferred.
- [x] Finalen PR-Dateiscope geprüft: nur `src/agent_brain/contracts/`, `tests/contracts/`, neutrale Fixtures sowie Contract-/Navigationsdoku.
- [x] Keine Runtime-Dependency geändert.
- [x] Generischen Code und neutrale Fixtures auf Claire/CDB/Trading/LR/Echtgeld/`surrealdb-local`/private-MCP-Leaks auditiert; keine gefunden.
- [x] PR-Kommentare/Reviews/Threads geprüft; keine offenen Findings.
- [x] Review-Hardening test-first ergänzt: falsche primitive Typen und nicht-kanonische Schema-Strings fail-closed.
- [x] Exact code head `277d5f38e75c094c190187e47b35127c6db1ddb5` in CI Run `39497197629` auf Python 3.12, 3.13 und 3.14 jeweils Install + Ruff + pytest GREEN.

## Post-Merge Delivery Gates

Diese Gates werden absichtlich nicht vorab als erledigte Checkboxes persistiert:

- Squash-merge PR #26 mit exact-head lease.
- Live-verify `main` SHA, PR merged state, Post-Merge-CI und Issue #15 close.
- Delivery-Evidence auf #15 und Epic #2 kommentieren; erst danach `DONE_MERGED_CLOSED` melden.
