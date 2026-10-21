# [SLICE 6] Knowledge Build, Seed und Import Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan. Implement tasks sequentially with mandatory testing checkpoints. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Issue #16 [SLICE 6]: deterministischer Knowledge-/Index-Build aus Slice-5-Ingestion-Outputs, Snapshot-/Schema-Versionierung, Manifest + Provenance (`source_ref` + `source_hash`), kontrollierter Import-Vertrag mit Pre-/Post-Validierung, idempotente Import-Semantik (Skip/Update/Tombstone), neutraler Fixture-Stand ohne Claire. Knowledge-Build-Writes sind NICHT Agent-Memory-Writes.

**Architecture:** Neuer Layer `src/agent_brain/knowledge/` konsumiert `agent_brain.connectors`-Outputs (offline, read-only), baut auf `agent_brain.contracts` auf. Store-Grenze neutral: In-Memory-Default, keine SurrealDB-Writes im Slice-6-Default (DB-Befuellung via dokumentierten Snapshot-Pfad; echte Migration = #21).

**Tech Stack:** Python >= 3.12, Standardbibliothek, pytest, Ruff. Keine neuen Runtime-Dependencies.

**Spec:** Issue #16 - `docs/START_HIER.md` - `docs/DATENFLUESSE.md` - `docs/extraction/COMPONENT_OWNERSHIP.md` - `docs/extraction/PARITY_GATES.md`

## Global Constraints

1. **Determinismus vor Convenience** - Byte-identischer kanonischer Snapshot bei gleichem Input + `RepositoryProfile`; alle Zeitstempel (`built_at`, Tombstone-Zeiten) injiziert; `datetime.now()`/`time.time()` verboten (Clock-Parameter).
2. **Provenance-Pflicht** - Jeder Record + Manifest-Quelle mit `source_ref` + `source_hash`, fail-closed.
3. **Schema-/Versionsdisziplin** - `schema_version` im Muster `knowledge-snapshot/v1`; Validierung via `require_compatible_version` (fail-closed, same-major additiv).
4. **Idempotenz ohne Hard-Delete** - identisch -> skip, geaendert -> update, fehlend -> Tombstone-Kandidat mit Reason (Parity zur Claire-Mechanik, agent-brain-eigene Typen).
5. **Atomar/fail-closed** - Validierung vor Write; Fehler -> result != OK ohne Partial-Commit; Secret-Redaction reuse aus Slice-5-Policy.
6. **Read-only Eingang** - Kein gh/HTTP/Git im Knowledge-Layer, nur Konsum von `RepositoryIngestionResult`; kein SurrealDB-Write im Default, keine produktiven Agent-Memory-Writes.
7. **12 Claire-Parity-Gate-Tests** bleiben charakterisierende Anker (keine Code-/Klassennamen-Uebernahme).
8. **Test-first RED->GREEN**, Ruff clean, statische Fixtures unter `tests/fixtures/knowledge/`.

---

### Task 1: Knowledge Snapshot Contract (AC4)

Create `src/agent_brain/knowledge/__init__.py`, `src/agent_brain/knowledge/snapshot.py`. Test `tests/knowledge/test_snapshot_contract.py`.

- [ ] Consumes: frozen-dataclass-/Post-Init-Version-Check-Muster + Schema-Version-Regex aus `agent_brain.contracts.versioning`; kanonische JSON-Konventionen aus `agent_brain.contracts.serialization`.
- [ ] Produces: `KNOWLEDGE_SNAPSHOT_SCHEMA = "knowledge-snapshot/v1"`, `KNOWLEDGE_MANIFEST_SCHEMA = "knowledge-manifest/v1"`, frozen dataclasses `BuildMetadata`, `KnowledgeManifest`, `KnowledgeSnapshot`.
- [ ] Steps: RED (Schema-Version-Ablehnung fail-closed, Frozen-Immutabilitaet, Manifest-Provenance-Pflicht) -> fokussierter pytest RED -> Implement -> Ruff -> Commit `feat: add knowledge snapshot contract`.

### Task 2: Deterministic Knowledge Builder (AC1, AC2)

Create `src/agent_brain/knowledge/builder.py`. Test `tests/knowledge/test_builder_determinism.py`.

- [ ] Consumes: `RepositoryIngestionResult` ("repository-ingestion/v1"), Contract-Familien, `build_ingestion_fingerprint`.
- [ ] Produces: `build_knowledge_snapshot(ingestion_result, *, clock=None, tool_version=str) -> KnowledgeSnapshot` mit `used_clock = clock or SystemClock()`; Records mit Pflicht-Provenance.
- [ ] Steps: RED (Byte-Identitaet zweier Builds, Clock-Injektion via FixedClock, Provenance-Fail-Closed, Profil-Fingerprint-Abhaengigkeit) -> Implement -> Ruff -> Commit `feat: add deterministic knowledge builder`.

### Task 3: Snapshot Serialization und Fail-Closed Validation (AC4)

Create `src/agent_brain/knowledge/serialization.py`. Test `tests/knowledge/test_snapshot_serialization.py`.

- [ ] Consumes: `contract_payload`/`serialize_contract` + `require_compatible_version`.
- [ ] Produces: `serialize_knowledge_snapshot(snapshot) -> str` (kanonisch, deterministisch), `parse_knowledge_snapshot(payload) -> KnowledgeSnapshot` (fail-closed inkl. Schema-Version-Check).
- [ ] Steps: RED (Roundtrip, deterministische Serialisierung, Ablehnung korrupter/fremder Versionen) -> Implement -> Ruff -> Commit `feat: add snapshot serialization with fail closed validation`.

### Task 4: Neutral Import Store und Adapter-Grenze (AC3, AC7)

Create `src/agent_brain/knowledge/import_store.py`. Test `tests/knowledge/test_import_store.py`.

- [ ] Consumes: `KnowledgeSnapshot`/`parse_knowledge_snapshot`.
- [ ] Produces: `SnapshotValidationReport` (ok|rejected + findings), `KnowledgeImportResult`, In-Memory-`KnowledgeImportStore` mit `apply_import(snapshot, *, clock)`, `iter_records()`, `current_tombstones()`; REFERENCE_ONLY als Default-Mode; Write-Surface nur eigener Store.
- [ ] Steps: RED (Store-Apply, REFERENCE_ONLY-Default, Validation-First -> rejected ohne Mutation, keine fremden Surfaces) -> Implement -> Ruff -> Commit `feat: add neutral knowledge import store`.

### Task 5: Idempotente Import Pipeline mit Tombstones (AC5)

Create `src/agent_brain/knowledge/import_pipeline.py`. Test `tests/knowledge/test_import_pipeline_idempotence.py`.

- [ ] Consumes: `KnowledgeImportStore`, Serialisierung/Validation, `canonical_hash`-basierte Record-IDs aus Slice 5.
- [ ] Produces: `import_knowledge_snapshot(store, snapshot, *, clock=None) -> KnowledgeImportResult`; Regeln: identisch -> `skipped`, geaendert -> `updated`, fehlend -> Tombstone (`record_removed_from_snapshot`, FixedClock-deterministisch); atomar (Validation-First, kein Partial-Commit).
- [ ] Steps: RED (skip/update/tombstone-Zweige, Cross-Run-Stabilitaet, rejected ohne Partial-Commit) -> Implement -> Ruff -> Commit `feat: add idempotent knowledge import pipeline`.

### Task 6: Neutraler Fixture und Dokumentation (AC6)

Create `tests/fixtures/knowledge/knowledge_snapshot.neutral.v1.json`, `tests/knowledge/test_neutral_fixture.py`. Extend `docs/START_HIER.md`, `docs/DATENFLUESSE.md`.

- [ ] Consumes: Builder + neutraler Ingestion-Eingang (statische Fixtures aus `tests/fixtures/connectors/`).
- [ ] Produces: committetes neutrales Fixture ohne Claire/live DB; Docs-Abschnitt Build/Seed/Import (Snapshot-Pfad, KB-Writes != Memory-Writes).
- [ ] Steps: RED-Fixture-Test (committed Fixture == kanonische Bytes des deterministischen Builds) -> RED-Run -> Fixture committen + Docs -> Ruff + fokussierte Tests -> Finale Gates `python -m pip install -e ".[dev]" && python -m ruff check . && python -m pytest -q` -> Commit `feat: add neutral knowledge snapshot fixture and seed docs`.

---

AC-Mapping: AC1->T2 - AC2->T1+T2 - AC3->T4 - AC4->T1+T3 - AC5->T5 - AC6->T6 - AC7->T4+T5.
