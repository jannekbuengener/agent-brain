# Shared Source / Index / Evidence Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slice #15 kanonisiert die gemeinsamen, produktneutralen Source-, Repository-, Index-/Graph- und Evidence-/Claim-Contracts, auf denen Context Package, Ingestion, Retrieval und Evidence Resolution anschließend gemeinsam aufbauen.

**Architecture:** Neue stabile Datentypen leben unter `agent_brain.contracts` und verwenden die gemergte Portable Foundation aus `agent_brain.core` für Canonical JSON/Hashing. Jeder Contract besitzt ein explizites `schema_version`-Feld. Additive Felder bleiben innerhalb derselben Major-Version lesbar; Breaking Changes benötigen eine neue Major-Version. Claire-spezifische Source-Namen, Trust-Scoring, Resolver-Logik, Required Reads, SurrealDB-Runtime und Trading-Policy bleiben außerhalb dieses Slices.

**Tech Stack:** Python >=3.12, Standardbibliothek, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-20-agent-brain-extraction-design.md` + Issue #15 + `docs/extraction/SLICE_0_EXTRACTION_CANON.md`

## Global Constraints

- Keine Imports aus `Claire_de_Binare`, `tools.surrealdb` oder Claire-`core.*`.
- Keine Repo-Ingestion, kein Retrieval, kein Context Package, kein Evidence Scoring/Resolver und keine SurrealDB-Runtime.
- Keine Claire-/CDB-/Trading-/LR-/Echtgeld-Namen oder Env-Variablen in generischen Contracts oder neutralen Fixtures.
- Produktive Agent-Memory-Writes bleiben `DEFER`.
- Keine neuen Runtime-Dependencies.
- Contracts sind frozen/immutable, deterministisch serialisierbar und besitzen explizite Schema-Versionen.
- Unbekannte additive Felder derselben Major-Version werden beim Lesen ignoriert; andere Contract-Familien oder Major-Versionen werden fail-closed abgelehnt.
- `EvidenceRef` und `ClaimRef` sind reine Referenz-/Datenverträge. Trust, Resolver und Scoring gehören erst in Slice #8.
- `RepositoryProfile` enthält nur generische Repo-/Ingestion-Grenzen. Konkrete Required Reads, Produktpfade und Policy bleiben Consumer-/Adapter-Scope.

## Review Focus

- Leere IDs, Source-Pfade, Hashes oder Repository-Bezeichner müssen fail-closed abgelehnt werden.
- Falsche Contract-Familie oder inkompatible Major-Version darf nicht still akzeptiert werden.
- Zusätzliche unbekannte Felder im selben `v1` dürfen Deserialisierung nicht brechen.
- Graph-Edges mit leerem Endpoint/Typ oder Confidence außerhalb `[0.0, 1.0]` sind ungültig.
- Evidence-/Claim-Refs dürfen keine Trust-Klasse, DB-Autorität oder Resolver-Entscheidung vortäuschen.

---

### Task 1: Contract-Versionierung und Serialisierungsbasis

**Files:**
- Create: `src/agent_brain/contracts/__init__.py`
- Create: `src/agent_brain/contracts/versioning.py`
- Create: `src/agent_brain/contracts/serialization.py`
- Test: `tests/contracts/test_versioning.py`

**Interfaces:**
- Consumes: `agent_brain.core.canonical.canonical_json_dumps`.
- Produces: `ContractVersion`, `require_compatible_version(value: str, expected_family: str, supported_major: int) -> ContractVersion`, `serialize_contract(payload: Mapping[str, object]) -> str`.

- [ ] Write RED tests for `repository-source/v1`, malformed/blank versions, wrong family and wrong major.
- [ ] Run `python -m pytest tests/contracts/test_versioning.py -q`; expected RED because `agent_brain.contracts` does not exist.
- [ ] Implement minimal parser/compatibility helper + canonical serializer; no generic schema framework.
- [ ] Run focused pytest + Ruff; require GREEN.
- [ ] Commit `feat: add shared contract versioning baseline`.

### Task 2: RepositorySource, RepositoryProfile und ArtifactRef

**Files:**
- Create: `src/agent_brain/contracts/repository.py`
- Test: `tests/contracts/test_repository_contracts.py`
- Create: `tests/fixtures/contracts/repository_profile.neutral.v1.json`

**Interfaces:**
- Consumes: `require_compatible_version`.
- Produces:
  - `RepositorySource(schema_version: str, source_id: str, repository: str, revision: str | None = None, source_uri: str | None = None)`
  - `RepositoryProfile(schema_version: str, profile_id: str, source: RepositorySource, include_paths: tuple[str, ...] = (), exclude_paths: tuple[str, ...] = (), allowed_file_types: tuple[str, ...] = (), metadata: Mapping[str, object] = field(default_factory=dict))`
  - `ArtifactRef(schema_version: str, artifact_id: str, source_id: str, source_path: str, source_hash: str, revision: str | None = None)`
  - `to_dict()` and `from_dict(payload: Mapping[str, object])` on each type.

- [ ] Write RED round-trip tests with neutral repo `example/widgets`, revision `abc123`, paths `src/` and `docs/`.
- [ ] Add validation tests for blank repository/source/profile/artifact IDs, source path and source hash.
- [ ] Add same-major additive-field test: unknown payload field must not break `from_dict`.
- [ ] Run focused tests; expected RED.
- [ ] Implement minimal frozen dataclasses with normalized non-empty text, tuple conversion and safe mapping copy; no filesystem/discovery behavior.
- [ ] Verify neutral fixture round-trip is deterministic.
- [ ] Commit `feat: define repository source and profile contracts`.

### Task 3: Minimal Index-/Graph-Record-Contracts

**Files:**
- Create: `src/agent_brain/contracts/index.py`
- Test: `tests/contracts/test_index_contracts.py`
- Create: `tests/fixtures/contracts/index_graph.neutral.v1.json`

**Interfaces:**
- Consumes: `ArtifactRef`, `require_compatible_version`, `canonical_hash`.
- Produces:
  - `IndexRecord(schema_version: str, record_id: str, record_type: str, source: ArtifactRef, content_hash: str | None = None, attributes: Mapping[str, object] = field(default_factory=dict))`
  - `GraphEdge(schema_version: str, edge_id: str, from_id: str, to_id: str, edge_type: str, source: ArtifactRef | None = None, confidence: float = 1.0, inferred: bool = False)`
  - `graph_fingerprint(records: Sequence[IndexRecord], edges: Sequence[GraphEdge]) -> str` excluding run IDs/timestamps.
  - `to_dict()` / `from_dict()` on both types.

- [ ] Characterize portable expectations from Claire `test_context_graph_contract.py`: deterministic structural fingerprint, explicit IDs/endpoints and source refs.
- [ ] Write RED tests proving reordered equivalent inputs keep the same fingerprint and structural changes alter it.
- [ ] Add validation tests for blank IDs/types/endpoints and invalid confidence.
- [ ] Run focused tests; expected RED.
- [ ] Implement structural contracts + deterministic fingerprint only. Duplicate/orphan/stale-link analysis remains later validation/runtime scope.
- [ ] Verify neutral fixture round-trip + fingerprint.
- [ ] Commit `feat: define shared index graph contracts`.

### Task 4: EvidenceRef und ClaimRef ohne Resolver-/Trust-Logik

**Files:**
- Create: `src/agent_brain/contracts/evidence.py`
- Test: `tests/contracts/test_evidence_contracts.py`
- Create: `tests/fixtures/contracts/evidence_claim.neutral.v1.json`

**Interfaces:**
- Consumes: `require_compatible_version`.
- Produces:
  - `EvidenceRef(schema_version: str, evidence_id: str, evidence_type: str, source_refs: tuple[str, ...] = (), artifact_refs: tuple[str, ...] = (), claim_refs: tuple[str, ...] = (), decision_refs: tuple[str, ...] = (), content_hash: str | None = None, summary: str | None = None)`
  - `ClaimRef(schema_version: str, claim_id: str, claim_type: str, statement: str | None = None, evidence_refs: tuple[str, ...] = (), artifact_refs: tuple[str, ...] = (), decision_refs: tuple[str, ...] = (), source_refs: tuple[str, ...] = ())`
  - `to_dict()` / `from_dict()` on both types.

- [ ] Characterize portable fields from Claire `test_wave14_context_record_schemas.py`, `db_record_evidence_contract.py` and `contradiction_scan.py`; retain identity/reference/summary relations only.
- [ ] Write RED tests for canonical round-trips and empty optional relation lists.
- [ ] Add test where extra `trust_classification`, `brain_source` and DB metadata are ignored as unknown additive data and are not exposed as contract authority.
- [ ] Add validation tests for blank evidence/claim IDs and types.
- [ ] Run focused tests; expected RED.
- [ ] Implement minimal refs. Do not port `classify_trust`, DB proof, source-priority enums, freshness scoring, resolver behavior or Claire tool names.
- [ ] Verify neutral fixture round-trip.
- [ ] Commit `feat: define evidence and claim reference contracts`.

### Task 5: Registry, Producer-/Consumer-Richtung und Kompatibilitätsdoku

**Files:**
- Create: `src/agent_brain/contracts/registry.py`
- Test: `tests/contracts/test_registry.py`
- Create: `docs/contracts/README.md`
- Modify: `README.md`
- Modify: `docs/START_HIER.md`
- Modify: `docs/DEVELOPMENT.md`

**Interfaces:**
- Consumes: schema constants from Tasks 1–4.
- Produces: `CONTRACT_SCHEMAS: Mapping[str, str]` mit genau einer kanonischen Version pro Contract-Familie.

- [ ] Write registry RED test for repository source/profile/artifact, index record/graph edge, evidence ref and claim ref families.
- [ ] Implement static registry metadata only; no plugin/discovery runtime.
- [ ] Document producer/consumer direction: #6 consumes profile/refs; #9 produces repository/artifact/index records; #7 consumes index/graph; #8 resolves evidence/claims; #16 persists build outputs; #21 consumes schema foundation for handoff.
- [ ] Document compatibility: same family+major permits additive optional fields; required-field removal/addition, type or semantic break requires `/v2`.
- [ ] Update navigation/status so #15 is current baseline and #6 becomes next linear slice after merge.
- [ ] Run full Ruff + pytest.
- [ ] Commit `docs: publish shared contract ownership and compatibility`.

### Task 6: Final Scope-/Parity-Audit und Delivery

**Files:**
- Modify: this plan only if completion checkboxes are useful.

- [ ] Map Claire parity gates `test_context_graph_contract.py`, `test_db_record_evidence_contract.py`, `test_wave14_context_record_schemas.py` to Agent-Brain tests; explicitly record deferred trust/resolver/runtime behavior.
- [ ] Scan generic code/fixtures for Claire/CDB/trading/echtgeld/LR/`surrealdb-local`, concrete Claire paths and private-MCP assumptions; generic contract leakage is a failure.
- [ ] Confirm no runtime dependency added and changed code stays under `src/agent_brain/contracts/`, `tests/contracts/`, neutral fixtures and contract/navigation docs.
- [ ] Run CI on Python 3.12 / 3.13 / 3.14.
- [ ] Review PR diff, reviews and threads; fix only #15-scope findings.
- [ ] Squash-merge with exact-head lease once green.
- [ ] Live-verify main SHA, PR merged state, post-merge CI and Issue #15 close.
- [ ] Comment delivery evidence on #15 and Epic #2; mark `DONE_MERGED_CLOSED` only after every live check passes.
