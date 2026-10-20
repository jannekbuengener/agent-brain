# Repository Ingestion and Connectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slice #9 generalisiert Repository-Inventar, lokale Offline-Ingestion, statische Source-/Index-Extraktion und portable Ledger-Source-Normalisierung so, dass beliebige explizit profilierte Repositories deterministische #15-Contracts für den späteren Knowledge-Build #16 erzeugen.

**Architecture:** `agent_brain.connectors` bleibt read-only/offline und baut ausschließlich auf `RepositorySource`, `RepositoryProfile`, `ArtifactRef`, `IndexRecord` und `GraphEdge` aus Slice #15 auf. Ein explizites RepositoryProfile plus produktneutrale Ingestion-Regeln steuert Include/Exclude, Dateitypen, Sensitivity und Forbidden-Regeln; lokaler Pfad, konfigurierte Upstream-Identität und beobachteter Git-Origin bleiben getrennte Evidence-Felder. Der Slice liest lokale Dateien und optional lokale Git-Metadaten, klont/mutiert nichts, kontaktiert GitHub nicht und schreibt weder SurrealDB noch Agent Memory.

**Tech Stack:** Python >=3.12, Standardbibliothek, pytest, Ruff. Keine neuen Runtime-Dependencies.

**Spec:** `docs/superpowers/specs/2026-10-20-agent-brain-extraction-design.md` + Issue #9 + `docs/extraction/COMPONENT_OWNERSHIP.md` + `docs/extraction/PARITY_GATES.md`

## Global Constraints

- Keine Imports aus `Claire_de_Binare`, `tools.surrealdb`, Claire-`core.*` oder privaten MCP-/Operator-Flächen.
- Keine SurrealDB-Verbindung, keine DB-Befüllung, kein HTTP-/GitHub-Netzwerkzugriff, kein Clone, kein Checkout, keine Repository-Mutation.
- Keine produktiven Agent-Memory-Writes.
- Keine hardcodierten Claire-/CDB-/Trading-/LR-/Live-Go-/Echtgeld-Pfade, Modulpräfixe, Root-Namen oder Source-Namen im generischen Runtime-Code oder neutralen Fixtures.
- `RepositorySource`, `RepositoryProfile`, `ArtifactRef`, `IndexRecord` und `GraphEdge` aus #15 werden konsumiert und nicht dupliziert.
- `RepositoryProfile.include_paths`, `exclude_paths` und `allowed_file_types` bleiben die kanonische Profilgrenze; zusätzliche Sensitivity-/Forbidden-/Limit-Regeln liegen in einer separaten Ingestion-Policy statt `repository-profile/v1` rückwirkend zu brechen.
- Lokaler Ordnername oder Workspace-Position beweist weder Remote-Ownership noch Supportstatus. Lokale Pfadidentität, konfigurierte Source-Identität und beobachteter Git-Origin bleiben separat.
- Alle IDs/Fingerprints sind deterministisch und unabhängig von Dateisystem-Iteration, Wall Clock und absolutem Host-Pfad.
- Text wird vor Hashing auf `\n` normalisiert; Binary/invalid UTF-8 wird nicht still als Text indexiert.
- Symlink-/Path-Escapes aus dem expliziten Repository-Root werden fail-closed ausgeschlossen.
- Forbidden-/Sensitivity-Regeln sind caller-supplied und fail-closed; kein Secret-Klartext darf in Findings, Records oder Fingerprints leaken.
- YAML-Ledger-Parsing und SurrealDB-HTTP/CREATE aus Claires `ledger_importer.py` werden nicht in diesen dependency-freien Core übernommen. #9 übernimmt nur portable Event-Normalisierung/Integritätsprüfung; konkrete Parser/Build-Persistenz folgen Adapter/#16-Scope.
- Der Output muss ohne DB-Runtime deterministisch von #16 weiterverarbeitet werden können.

## Review Focus

- Symlink-, `..`-, absolute und case/path-normalization escapes müssen außerhalb des Root fail-closed bleiben und dürfen nie gelesen werden.
- Ein lokaler Ordner mit abweichendem `origin` darf die konfigurierte `RepositorySource` nicht überschreiben; der Mismatch wird Evidence, nicht automatische Umdeutung.
- Binary-, invalid-UTF8- und oversized Dateien dürfen den Lauf nicht abbrechen und dürfen keine halben `ArtifactRef`/`IndexRecord` erzeugen.
- Python-Syntaxfehler müssen als Finding erscheinen, während andere Dateien/Records deterministisch weiter indexiert werden.
- Forbidden-/Sensitive-Inhalte müssen vor Record-/Finding-Ausgabe redigiert oder vollständig ausgeschlossen werden; Secret-only Änderungen dürfen keine Klartext-Spuren erzeugen.

---

### Task 1: Ingestion Policy and Stable Output Contract

**Files:**
- Create: `src/agent_brain/connectors/ingestion.py`
- Test: `tests/connectors/test_ingestion_contract.py`
- Create: `tests/fixtures/connectors/repository_ingestion_profile.neutral.v1.json`

**Interfaces:**
- Consumes: `RepositorySource`, `RepositoryProfile`, `ArtifactRef`, `IndexRecord`, `GraphEdge`, `canonical_hash`.
- Produces:
  - `INGESTION_RESULT_SCHEMA = "repository-ingestion/v1"`
  - `SensitivityRule(path_pattern: str, classification: str, reason: str)`
  - `ForbiddenRule(pattern: str, target: Literal["path", "content"], reason: str)`
  - `IngestionPolicy(sensitivity_rules: tuple[SensitivityRule, ...] = (), forbidden_rules: tuple[ForbiddenRule, ...] = (), max_file_size_bytes: int = 1_000_000, local_module_prefixes: tuple[str, ...] = ())`
  - `IngestionFinding(source_path: str, status: Literal["skipped", "forbidden", "limited"], reason: str, sensitivity: str | None = None)`
  - `RepositoryIngestionResult(schema_version: str, source: RepositorySource, profile_id: str, artifacts: tuple[ArtifactRef, ...], records: tuple[IndexRecord, ...], edges: tuple[GraphEdge, ...], findings: tuple[IngestionFinding, ...], fingerprint: str)` with `to_dict()`.
  - `build_ingestion_fingerprint(*, source: RepositorySource, profile_id: str, artifacts: Sequence[ArtifactRef], records: Sequence[IndexRecord], edges: Sequence[GraphEdge], findings: Sequence[IngestionFinding]) -> str`.

- [ ] **Step 1: Write RED contract tests** for schema/version, frozen inputs, positive max-size, valid forbidden targets, stable serialization and use of the exact #15 contract types.
- [ ] **Step 2: Add RED fingerprint tests** proving input-order independence and proving absolute host root / wall-clock data is not part of the fingerprint.
- [ ] **Step 3: Run focused pytest**; expected RED because `agent_brain.connectors.ingestion` does not exist.
- [ ] **Step 4: Implement the minimal dataclasses and fingerprint builder** using canonical hashing and sorted `to_dict()` payloads. Do not add filesystem behavior yet.
- [ ] **Step 5: Run `python -m ruff check src/agent_brain/connectors tests/connectors` and focused pytest**; expected PASS.
- [ ] **Step 6: Commit** `feat: add repository ingestion contracts`.

### Task 2: Repository / Workspace Inventory With Separate Local and Remote Identity

**Files:**
- Create: `src/agent_brain/connectors/inventory.py`
- Test: `tests/connectors/test_inventory.py`
- Create: `tests/fixtures/connectors/repository_inventory.neutral.v1.json`

**Interfaces:**
- Consumes: `RepositoryProfile` from Task 1 / #15.
- Produces:
  - `INVENTORY_SCHEMA = "repository-inventory/v1"`
  - `RepositoryInventorySpec(key: str, local_root: Path, profile: RepositoryProfile, required: bool = False)`
  - `RepositoryInventoryEntry(key: str, local_path: str, local_status: Literal["OK", "MISSING", "LIMITED"], source_id: str, repository: str, configured_source_uri: str | None, observed_origin_uri: str | None, origin_matches_profile: bool | None, limitations: tuple[str, ...], required: bool)`
  - `RepositoryInventoryReport(schema_version: str, entries: tuple[RepositoryInventoryEntry, ...], verdict: Literal["pass", "pass_with_limits", "fail"], fingerprint: str)` with `to_dict()`.
  - `read_git_origin(root: Path) -> str | None` — read-only local `git -C <root> remote get-url origin`; no fetch/remote contact.
  - `build_repository_inventory(specs: Sequence[RepositoryInventorySpec], *, origin_reader: Callable[[Path], str | None] = read_git_origin) -> RepositoryInventoryReport`.

- [ ] **Step 1: Write RED tests** for required OK/MISSING handling, optional missing -> `pass_with_limits`, deterministic ordering/fingerprint and no network/clone behavior.
- [ ] **Step 2: Add the identity-separation RED test:** local folder name intentionally differs from configured repository; observed origin intentionally differs from `source_uri`; keep all three values, set `origin_matches_profile=False`, add limitation, and never rewrite `RepositorySource`.
- [ ] **Step 3: Add RED tests** for `.git` absent / origin absent / git unavailable -> `LIMITED` evidence instead of false PASS or crash.
- [ ] **Step 4: Run focused pytest**; expected RED.
- [ ] **Step 5: Implement local-only inventory and injected/default origin reader.** No `gh`, HTTP or clone support in this slice.
- [ ] **Step 6: Verify Ruff + focused tests**.
- [ ] **Step 7: Commit** `feat: add repository inventory connector`.

### Task 3: Safe Filesystem Discovery and Artifact Scanning

**Files:**
- Create: `src/agent_brain/connectors/scanner.py`
- Test: `tests/connectors/test_scanner.py`
- Create fixture tree under `tests/fixtures/connectors/repository_neutral/`:
  - `src/widget.py`
  - `src/broken.py`
  - `docs/widget.md`
  - `config/settings.toml`
  - `excluded/ignore.py`
  - `forbidden/private.txt`

**Interfaces:**
- Consumes: `RepositoryProfile`, `IngestionPolicy`, `ArtifactRef`, Foundation canonical hashing/redaction.
- Produces:
  - `ScannedSource(ref: ArtifactRef, file_type: str, sensitivity: str, size_bytes: int, text: str)` — in-memory only; no public serialization of raw content.
  - `ScanResult(sources: tuple[ScannedSource, ...], findings: tuple[IngestionFinding, ...])`.
  - `classify_file_type(path: str) -> str | None` for generic built-ins: `python`, `markdown`, `toml`, `json`, `yaml`, `text`.
  - `scan_repository(root: Path, profile: RepositoryProfile, policy: IngestionPolicy) -> ScanResult`.

- [ ] **Step 1: Write RED fixture tests** for include/exclude precedence, allowed file types, deterministic path order, LF/CRLF-normalized source hash and stable `artifact_id` from source-id/path/hash.
- [ ] **Step 2: Add RED containment tests** for symlink outside root, `..` escape and absolute include/exclude attempts. Escapes become `forbidden` findings and are never opened.
- [ ] **Step 3: Add RED robustness tests** for oversized, binary/NUL and invalid UTF-8 files -> deterministic findings, no artifact.
- [ ] **Step 4: Add RED Sensitivity/Forbidden tests** proving caller patterns classify or exclude files and emitted findings contain no matching secret value.
- [ ] **Step 5: Run focused pytest**; expected RED.
- [ ] **Step 6: Implement safe discovery/read/hash** with `Path.resolve()` containment, `fnmatch`/prefix matching and standard-library-only text handling.
- [ ] **Step 7: Verify Ruff + focused tests**.
- [ ] **Step 8: Commit** `feat: add safe repository scanner`.

### Task 4: Static Source Index and Graph Extraction

**Files:**
- Create: `src/agent_brain/connectors/indexer.py`
- Test: `tests/connectors/test_indexer.py`
- Extend: `tests/fixtures/connectors/repository_neutral/`

**Interfaces:**
- Consumes: `ScannedSource`, `ScanResult`, `RepositoryProfile`, `IngestionPolicy`, `IndexRecord`, `GraphEdge`.
- Produces:
  - `extract_python_records(source: ScannedSource, *, local_module_prefixes: tuple[str, ...]) -> tuple[tuple[IndexRecord, ...], tuple[GraphEdge, ...], tuple[IngestionFinding, ...]]`
  - `extract_markdown_records(source: ScannedSource) -> tuple[tuple[IndexRecord, ...], tuple[GraphEdge, ...]]`
  - `extract_config_records(source: ScannedSource) -> tuple[IndexRecord, ...]` for TOML/JSON only; secret-like config values use core redaction/hash markers, never raw values.
  - `build_repository_index(root: Path, profile: RepositoryProfile, policy: IngestionPolicy) -> RepositoryIngestionResult`.

**Record vocabulary for this slice:**
- `repository_file`
- `document_section`
- `document_chunk`
- `code_symbol`
- `import_reference`
- `test_case`
- `config_reference`
- `doc_code_reference`

**Graph-edge vocabulary for this slice:**
- `contains`
- `imports`
- `tests`
- `references`

- [ ] **Step 1: Write RED Python-AST tests** characterizing portable Claire behavior: functions/classes/methods/async/decorators, test-function detection, relative import locality and syntax-error finding without whole-run failure.
- [ ] **Step 2: Add RED locality tests** proving no built-in `core/services/tools/...` prefixes; only `IngestionPolicy.local_module_prefixes` classify absolute imports as local, while relative imports are local by syntax.
- [ ] **Step 3: Add RED Markdown/config tests** for sections/chunks, backtick symbol references, TOML/JSON flattened config refs and redacted sensitive values.
- [ ] **Step 4: Add RED graph tests** for deterministic `contains/imports/tests/references` edges and stable result fingerprint under different filesystem iteration order.
- [ ] **Step 5: Add RED end-to-end neutral fixture test:** an arbitrary `example/widgets` RepositoryProfile produces only #15 `ArtifactRef`/`IndexRecord`/`GraphEdge` outputs and no product-specific vocabulary.
- [ ] **Step 6: Run focused pytest**; expected RED.
- [ ] **Step 7: Implement minimal extractors and `build_repository_index`.** Reuse `ast`, `tomllib`, `json`, core canonical hashing/redaction; do not add YAML parser or DB behavior.
- [ ] **Step 8: Verify Ruff + focused tests**.
- [ ] **Step 9: Commit** `feat: add portable repository indexer`.

### Task 5: Portable Ledger/Event Source Normalization

**Files:**
- Create: `src/agent_brain/connectors/ledger.py`
- Test: `tests/connectors/test_ledger.py`
- Create: `tests/fixtures/connectors/ledger_events.neutral.v1.json`

**Interfaces:**
- Consumes: caller-supplied `Sequence[Mapping[str, object]]`, source `ArtifactRef`, core canonical hashing/redaction, `IndexRecord`.
- Produces:
  - `LedgerIntegrityError(code: str, reason: str, event_ids: tuple[str, ...] = ())`
  - `normalize_ledger_events(events: Sequence[Mapping[str, object]], *, source: ArtifactRef) -> tuple[IndexRecord, ...]`.

**Portable behavior retained from Claire:**
- deterministic event ordering by timestamp + event-id;
- deterministic fallback event-id when absent;
- per-agent previous-event chain as data only;
- declared SHA-256 mismatch -> fail closed;
- signature present without injected verifier -> fail closed (`signature_unsupported`), malformed/blank signature -> fail closed;
- evidence text is redacted before output;
- records use `record_type="ledger_event"` and #15 `IndexRecord`/`ArtifactRef` contracts.

**Explicitly not ported in #9:** YAML loader, `requests`, SurrealDB `ImportConfig`, lookup/preflight queries, `CREATE/UPSERT/MERGE` builders, namespace/database/auth, duplicate DB lookup or any database write.

- [ ] **Step 1: Write RED normalization tests** for deterministic ordering/chain, redacted evidence, stable hashes and shared `IndexRecord` source refs.
- [ ] **Step 2: Write RED integrity tests** for hash mismatch, blank signature and unsupported signature; no output records on failed batch validation.
- [ ] **Step 3: Add RED scope test** proving module source contains no `requests`, SurrealQL verbs, DB namespace/database/auth or YAML runtime dependency.
- [ ] **Step 4: Run focused pytest**; expected RED.
- [ ] **Step 5: Implement portable normalization only.** Batch preflight all integrity constraints before returning any records.
- [ ] **Step 6: Verify Ruff + focused tests**.
- [ ] **Step 7: Commit** `feat: add portable ledger source normalization`.

### Task 6: Public Surface, Documentation, Research Reference and Delivery Audit

**Files:**
- Modify: `src/agent_brain/connectors/__init__.py`
- Create: `docs/connectors/README.md`
- Modify: `README.md`
- Modify: `docs/START_HIER.md`
- Modify: `docs/DEVELOPMENT.md`
- Modify: `docs/external-docs/index.md`
- Create: `tests/connectors/test_product_neutrality.py`
- Create: `tests/connectors/test_public_surface.py`
- Modify: this plan only for truthful completion/evidence notes; do not pre-check merge/post-merge steps.

**Interfaces:**
- Produces stable public imports for Slice #9 from `agent_brain.connectors`; no CLI/MCP/DB surface.

- [ ] **Step 1: Write RED public-surface test** covering Task 1–5 public contracts/builders only.
- [ ] **Step 2: Write RED product-neutrality test** scanning `src/agent_brain/connectors/` and neutral fixtures for Claire/CDB/trading/echtgeld/live-go/LR-/MEXC/private-MCP/SurrealDB-local leaks.
- [ ] **Step 3: Export the stable Slice-5 surface** from `agent_brain.connectors`.
- [ ] **Step 4: Document ownership/consumer direction:** #9 reads explicit local repos and emits #15 contracts; #16 owns build/persist; #7 retrieval; #10 SurrealDB read; #13 Claire adapter.
- [ ] **Step 5: Document parity mapping** from Claire baseline `test_context_indexer.py`, `test_context_symbol_extraction.py`, portable parts of `test_ledger_importer.py`, and `test_cross_repo_root_inventory.py`; explicitly record DB/YAML/CLI/network behavior as deferred or adapter-owned.
- [ ] **Step 6: Update external reference index with the local SurrealDB research landscape as `REFERENCE`, not `ACTIVE`.** Record the agent rule derived from the supplied landscape: local workspace placement/dirname does not establish upstream ownership/support; inspect configured origin and current upstream/docs before reuse. Do not hardcode `D:\Dev\Workspaces\Database` into runtime defaults.
- [ ] **Step 7: Update navigation/status to `SLICE_5_REPOSITORY_INGESTION`; next linear slice becomes #16.** Keep #21 separate.
- [ ] **Step 8: Confirm `pyproject.toml` runtime dependencies remain `[]`.**
- [ ] **Step 9: Run full CI on Python 3.12 / 3.13 / 3.14** and inspect exact-head install + Ruff + pytest results.
- [ ] **Step 10: Review full PR diff, comments/reviews/threads and exact main/head SHAs.** Fix only #9/user-directed docs scope findings.
- [ ] **Step 11: Squash-merge with exact-head lease**, then live-verify main SHA, PR merged state, Issue #9 close and post-merge CI.
- [ ] **Step 12: Comment delivery evidence on #9 and Epic #2.** Use `DONE_MERGED_CLOSED` only after implementation, merge, issue closure and post-merge CI are all live-confirmed.
