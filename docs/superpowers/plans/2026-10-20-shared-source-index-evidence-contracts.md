# Shared Source / Index / Evidence Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slice #15 kanonisiert die gemeinsamen, produktneutralen Source-, Repository-, Index-/Graph- und Evidence-/Claim-Contracts, auf denen Context Package, Ingestion, Retrieval und Evidence Resolution anschließend gemeinsam aufbauen.

**Architecture:** Neue stabile Datentypen leben unter `agent_brain.contracts` und verwenden ausschließlich die bereits gemergte Portable Foundation aus `agent_brain.core`. Die Contracts besitzen explizite `schema_version`-Felder, deterministische Serialisierung und eine kleine Kompatibilitätsregel: additive Felder bleiben innerhalb derselben Major-Version lesbar, Breaking Changes benötigen eine neue Major-Version. Claire-spezifische Source-Namen, Trust-Scoring, Resolver-Logik, Required Reads, SurrealDB-Runtime und Trading-Policy bleiben außerhalb dieses Slices.

**Tech Stack:** Python >=3.12, Standardbibliothek, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-20-agent-brain-extraction-design.md` + Issue #15 + `docs/extraction/SLICE_0_EXTRACTION_CANON.md`

## Global Constraints

- Keine Imports aus `Claire_de_Binare`, `tools.surrealdb` oder Claire-`core.*`.
- Keine Repo-Ingestion, kein Retrieval, kein Context Package, kein Evidence Scoring/Resolver und keine SurrealDB-Runtime.
- Keine Claire-/CDB-/Trading-/LR-/Echtgeld-Namen oder Env-Variablen in generischen Contracts oder neutralen Fixtures.
- Produktive Agent-Memory-Writes bleiben `DEFER`.
- Keine neuen Runtime-Dependencies.
- Source-/Index-/Evidence-Contracts sind immutable/frozen, serialisierbar und besitzen explizite Schema-Versionen.
- Additive Payload-Felder innerhalb derselben Major-Version dürfen ältere Reader nicht brechen; unbekannte Felder werden beim Lesen ignoriert. Eine andere Major-Version wird fail-closed abgelehnt.
- `EvidenceRef` und `ClaimRef` sind Referenz-/Datenverträge; Trust-/Resolver-/Scoring-Logik gehört erst in Slice #8.
- `RepositoryProfile` enthält nur generische Repo- und Ingestion-Grenzen. Konkrete Claire Required Reads, Trading-State-Pfade und Produktpolicy bleiben Consumer-/Adapter-Scope.

## Review Focus

- Leere IDs, Source-Pfade, Hashes oder Repository-Bezeichner müssen fail-closed abgelehnt werden.
- Schema-Familie oder Major-Version darf nicht still akzeptiert werden, wenn sie inkompatibel ist.
- Zusätzliche unbekannte Felder im selben `v1` dürfen Deserialisierung nicht brechen.
- Graph-Edges mit leerem Endpoint oder leerem Edge-Typ dürfen nicht als gültige Contracts entstehen.
- Evidence-/Claim-Refs dürfen keine Resolver-Entscheidung, Trust-Klasse oder DB-Autorität vortäuschen.

---

### Task 1: Contract-Versionierung und gemeinsame Serialisierungsbasis

**Files:**
- Create: `src/agent_brain/contracts/__init__.py`
- Create: `src/agent_brain/contracts/versioning.py`
- Create: `src/agent_brain/contracts/serialization.py`
- Create: `tests/contracts/test_versioning.py`

**Interfaces:**
- Consumes: `agent_brain.core.canonical.canonical_json_dumps`
- Produces: `ContractVersion`, `require_compatible_version(value: str, expected_family: str, supported_major: int) -> ContractVersion`, `contract_payload(**fields) -> dict[str, object]`, `serialize_contract(payload: Mapping[str, object]) -> str`.

- [ ] **Step 1: Write RED tests** for parsing `repository-source/v1`, rejecting blank/malformed versions and rejecting another family/major.
- [ ] **Step 2: Add forward-compatible payload test** proving an unknown additive field on the same `v1` can be ignored by downstream `from_dict` readers.
- [ ] **Step 3: Run `python -m pytest tests/contracts/test_versioning.py -q`** and confirm RED because `agent_brain.contracts` does not exist.
- [ ] **Step 4: Implement minimal version parser/compatibility helper and canonical serializer.** No generic schema framework or third-party dependency.
- [ ] **Step 5: Run focused test + Ruff** and require GREEN.
- [ ] **Step 6: Commit** `feat: add shared contract versioning baseline`.

### Task 2: RepositorySource, RepositoryProfile und ArtifactRef

**Files:**
- Create: `src/agent_brain/contracts/repository.py`
- Create: `tests/contracts/test_repository_contracts.py`
- Create: `tests/fixtures/contracts/repository_profile.neutral.v1.json`

**Interfaces:**
- Consumes: `require_compatible_version`, `StableIdentity`, `ProvenanceStamp`.
- Produces:
  - `RepositorySource(schema_version: str, source_id: str, repository: str, revision: str | None = None, source_uri: str | None = None)`
  - `RepositoryProfile(schema_version: str, profile_id: str, source: RepositorySource, include_paths: tuple[str, ...] = (), exclude_paths: tuple[str, ...] = (), allowed_file_types: tuple[str, ...] = (), metadata: Mapping[str, object] = {})`
  - `ArtifactRef(schema_version: str, artifact_id: str, source_id: str, source_path: str, source_hash: str, revision: str | None = None)`
  - each type: `to_dict() -> dict[str, object]` and `from_dict(payload: Mapping[str, object]) -> Self`.

- [ ] **Step 1: Write RED round-trip tests** using neutral repo `example/widgets`, revision `abc123`, paths `src/` and `docs/`.
- [ ] **Step 2: Write validation tests** for blank repository/source/profile/artifact IDs, blank `source_path`, and blank `source_hash`.
- [ ] **Step 3: Write additive-compatibility test** with an unknown payload field under the same `repository-profile/v1`.
- [ ] **Step 4: Run focused tests** and confirm RED because repository contracts are absent.
- [ ] **Step 5: Implement minimal frozen dataclasses** with normalized non-empty text and tuple conversion; no filesystem access and no repository discovery logic.
- [ ] **Step 6: Verify fixture deserializes and reserializes deterministically.**
- [ ] **Step 7: Commit** `feat: define repository source and profile contracts`.

### Task 3: Minimal Index-/Graph-Record-Contracts

**Files:**
- Create: `src/agent_brain/contracts/index.py`
- Create: `tests/contracts/test_index_contracts.py`
- Create: `tests/fixtures/contracts/index_graph.neutral.v1.json`

**Interfaces:**
- Consumes: `ArtifactRef`, `require_compatible_version`, `canonical_hash`.
- Produces:
  - `IndexRecord(schema_version: str, record_id: str, record_type: str, source: ArtifactRef, content_hash: str | None = None, attributes: Mapping[str, object] = {})`
  - `GraphEdge(schema_version: str, edge_id: str, from_id: str, to_id: str, edge_type: str, source: ArtifactRef | None = None, confidence: float = 1.0, inferred: bool = False)`
  - `graph_fingerprint(records: Sequence[IndexRecord], edges: Sequence[GraphEdge]) -> str` excluding runtime timestamps/run IDs.
  - `to_dict()` / `from_dict()` on both record types.

- [ ] **Step 1: Characterize portable Claire expectations** from `test_context_graph_contract.py`: deterministic structural fingerprint, explicit node/edge IDs, source refs, and no orphan/resolver behavior in this base type layer.
- [ ] **Step 2: Write RED tests** proving stable fingerprint for reordered equivalent inputs and changed fingerprint when record/edge structure changes.
- [ ] **Step 3: Write validation tests** for blank IDs/types/endpoints and confidence outside `[0.0, 1.0]`.
- [ ] **Step 4: Run focused tests** and confirm RED.
- [ ] **Step 5: Implement only structural contracts + fingerprinting.** Duplicate/orphan/stale-link detection remains later ingestion/retrieval validation behavior, not embedded here.
- [ ] **Step 6: Verify neutral fixture round-trip and deterministic fingerprint.**
- [ ] **Step 7: Commit** `feat: define shared index graph contracts`.

### Task 4: EvidenceRef und ClaimRef ohne Resolver-/Trust-Logik

**Files:**
- Create: `src/agent_brain/contracts/evidence.py`
- Create: `tests/contracts/test_evidence_contracts.py`
- Create: `tests/fixtures/contracts/evidence_claim.neutral.v1.json`

**Interfaces:**
- Consumes: `ArtifactRef`, `require_compatible_version`, `canonical_hash`.
- Produces:
  - `EvidenceRef(schema_version: str, evidence_id: str, evidence_type: str, source_refs: tuple[str, ...] = (), artifact_refs: tuple[str, ...] = (), claim_refs: tuple[str, ...] = (), decision_refs: tuple[str, ...] = (), content_hash: str | None = None, summary: str | None = None)`
  - `ClaimRef(schema_version: str, claim_id: str, claim_type: str, statement: str | None = None, evidence_refs: tuple[str, ...] = (), artifact_refs: tuple[str, ...] = (), decision_refs: tuple[str, ...] = (), source_refs: tuple[str, ...] = ())`
  - `to_dict()` / `from_dict()` for both.

- [ ] **Step 1: Characterize portable Claire fields** from `test_wave14_context_record_schemas.py`, `db_record_evidence_contract.py` and `contradiction_scan.py`; keep only identity/reference/summary relations.
- [ ] **Step 2: Write RED tests** for alias-free canonical round trips and empty optional relation lists.
- [ ] **Step 3: Write negative test** proving payloads with unrelated extra `trust_classification`, `brain_source` or DB metadata are ignored as additive data and never exposed as contract authority.
- [ ] **Step 4: Write validation tests** for blank evidence/claim IDs and types.
- [ ] **Step 5: Run focused tests** and confirm RED.
- [ ] **Step 6: Implement minimal reference contracts.** Do not port `classify_trust`, DB record proof, source-priority enums, resolver logic, freshness scoring or Claire tool names.
- [ ] **Step 7: Verify neutral fixture round-trip.**
- [ ] **Step 8: Commit** `feat: define evidence and claim reference contracts`.

### Task 5: Contract Registry, Producer-/Consumer-Richtung und Kompatibilitätsdoku

**Files:**
- Create: `src/agent_brain/contracts/registry.py`
- Create: `docs/contracts/README.md`
- Modify: `README.md`
- Modify: `docs/START_HIER.md`
- Modify: `docs/DEVELOPMENT.md`
- Test: `tests/contracts/test_registry.py`

**Interfaces:**
- Consumes: schema constants from Tasks 1–4.
- Produces: `CONTRACT_SCHEMAS: Mapping[str, str]` with one canonical version string per shared contract family.

- [ ] **Step 1: Write registry RED test** requiring repository source/profile/artifact, index record/graph edge, evidence ref and claim ref families.
- [ ] **Step 2: Implement registry** as static metadata only; no plugin/discovery runtime.
- [ ] **Step 3: Document producer/consumer table:** #6 consumes refs/profile; #9 produces repository/artifact/index records; #7 consumes index/graph; #8 consumes/resolves evidence/claims; #16 persists build outputs; #21 consumes schema foundation for state handoff.
- [ ] **Step 4: Document compatibility rule:** same family + same major = additive-compatible when required v1 fields remain; new required field/removal/type semantic change = breaking and requires `/v2`.
- [ ] **Step 5: Update navigation/status** so #15 is current baseline and #6 becomes next linear slice after merge.
- [ ] **Step 6: Run `python -m ruff check .` and `python -m pytest -q`.**
- [ ] **Step 7: Commit** `docs: publish shared contract ownership and compatibility`.

### Task 6: Final Scope-/Parity-Audit und Delivery

**Files:**
- Modify: `docs/superpowers/plans/2026-10-20-shared-source-index-evidence-contracts.md` only for completion checkboxes if useful.

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: merge-ready Slice #15 with no later-slice runtime behavior.

- [ ] **Step 1: Map Claire parity gates** `test_context_graph_contract.py`, `test_db_record_evidence_contract.py`, `test_wave14_context_record_schemas.py` to the new tests and record intentionally deferred resolver/trust/runtime behavior.
- [ ] **Step 2: Search changed generic code and fixtures** for `Claire`, `CDB`, `trading`, `echtgeld`, `LR`, `surrealdb-local`, concrete Claire paths and private MCP dependencies; fail if any leak is part of the generic contract.
- [ ] **Step 3: Confirm no runtime dependencies added** and no files outside `src/agent_brain/contracts/`, `tests/contracts/`, neutral contract fixtures and contract/navigation docs changed.
- [ ] **Step 4: Run full CI on Python 3.12 / 3.13 / 3.14.**
- [ ] **Step 5: Review PR diff, reviews and threads; fix only #15-scope findings.**
- [ ] **Step 6: Squash-merge with exact-head lease once green.**
- [ ] **Step 7: Live-verify main SHA, PR merged state, post-merge CI and automatic Issue #15 close.**
- [ ] **Step 8: Comment delivery evidence on #15 and Epic #2; mark `DONE_MERGED_CLOSED` only after all live checks pass.**
