# Context Package and Briefing Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slice #6 extrahiert den side-effect-freien Context-Package-/Briefing-Kern aus der gepinnten Claire-Baseline und baut ihn auf den gemergten Portable-Foundation- und Shared-Contract-Verträgen auf, ohne Claire-Produktpolicy, DB-Runtime, Retrieval oder Memory-Writes mitzuziehen.

**Architecture:** Neue fachliche Runtime lebt unter `agent_brain.context`. `ContextPackage` nutzt `ArtifactRef`, `EvidenceRef`, `SourcePriority`, Canonical Hashing, Clock und Redaction aus den bereits gemergten Schichten. Required Reads werden über ein injiziertes produktneutrales Profil aufgelöst; konkrete Claire-Reads bleiben Claire-Adapter-Scope. Briefing und Validation bleiben reine Daten-/Planungslogik; Consumer-spezifische Freigaben und Guardrails werden über vorhandene Policy-Hooks bzw. explizite Overlays injiziert.

**Tech Stack:** Python >=3.12, Standardbibliothek, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-20-agent-brain-extraction-design.md` + Issue #6 + `docs/extraction/COMPONENT_OWNERSHIP.md` + `docs/extraction/PARITY_GATES.md`

## Global Constraints

- Keine Imports aus `Claire_de_Binare`, `tools.surrealdb` oder Claire-`core.*`.
- Keine SurrealDB-Verbindung, kein MCP-/Protocol-Handler, kein Netzwerk, keine GitHub-Writes aus der Runtime.
- Keine produktiven Agent-Memory-Writes.
- Kein vollständiges Hybrid Retrieval, kein Evidence-/Claim-Resolver und kein Trust-Scoring.
- Keine Claire-/CDB-/Trading-/LR-/Live-Go-/Echtgeld-spezifischen Guardrails oder Required-Read-Pfade im generischen Runtime-Code oder neutralen Fixtures.
- `ArtifactRef`, `EvidenceRef`, `ClaimRef` und Repository-Source-Verträge aus #15 werden konsumiert und nicht dupliziert.
- Source-Priority kommt aus `agent_brain.core.source_priority.SourcePriority`; keine eingebauten Produktquellen.
- Redaction muss mindestens so streng wie die Claire-Charakterisierung sein; Secret-Werte dürfen weder Payload, Hash-relevante Klartexte noch Redaction-Summary leaken.
- IDs/Hashes sind deterministisch; Wall-Clock-Felder dürfen package-/briefing-IDs nicht verändern.
- Keine neuen Runtime-Dependencies.

## Review Focus

- Secret-only Änderungen in Artifacts/Required Reads/Links dürfen nach Redaction keinen anderen Context-Package-Hash erzeugen.
- Falsche Typen, leere IDs/Scopes und unsichere Required-Read-Pfade müssen fail-closed abgelehnt bzw. als nicht verfügbar markiert werden.
- Policy-Hook-Denials dürfen nur Approval-/Stop-Evidence erzeugen, niemals selbst eine Aktion autorisieren.
- Briefing-/Package-Ausgaben dürfen `EvidenceRef`/`ArtifactRef` nur serialisieren, nicht kopierte Konkurrenztypen etablieren.
- Generische Validation-/Explanation-Texte dürfen keine Claire-spezifischen Risk-, Trading-, LR- oder Echtgeld-Annahmen enthalten.

---

### Task 1: Portable Context Package v2

**Files:**
- Create: `src/agent_brain/context/__init__.py`
- Create: `src/agent_brain/context/package.py`
- Test: `tests/context/test_package.py`
- Create: `tests/fixtures/context/context_package.neutral.v2.json`

**Interfaces:**
- Consumes: `ArtifactRef`, `EvidenceRef`, `SourcePriority`, `canonical_hash`, `canonical_json_dumps`, `Clock`/`utcnow`, `redact_sensitive_mapping`.
- Produces:
  - `CONTEXT_PACKAGE_SCHEMA = "context-package/v2"`
  - `ContextArtifact(ref: ArtifactRef, artifact_type: str, summary: str | None = None, payload: Mapping[str, object] = ...)`
  - `ContextPackageRequest(target_scope: str, artifacts: tuple[ContextArtifact, ...], source_priority: SourcePriority, required_reads: tuple[Mapping[str, object], ...] = (), ranked_context: Mapping[str, object] | None = None, evidence_refs: tuple[EvidenceRef, ...] = (), decision_refs: tuple[str, ...] = (), guardrails: tuple[str, ...] = (), generated_at_or_as_of: str | None = None, clock: Clock | None = None)`
  - `ContextPackage(...).to_dict()`
  - `build_context_package(request: ContextPackageRequest) -> ContextPackage`

- [ ] Write RED tests for required schema fields, non-empty target/artifacts, use of shared `ArtifactRef`/`EvidenceRef`, deterministic `package_id`, artifact-order independence, wall-clock exclusion and neutral source-priority serialization.
- [ ] Add RED redaction tests mirroring Claire `test_context_package_v2.py`: sensitive keys, bearer/token-like text and secret URLs never leak; secret-only differences do not change `package_id`; redaction summary contains paths/types but no raw secret.
- [ ] Run focused pytest; expected RED because `agent_brain.context` does not exist.
- [ ] Implement minimal frozen dataclasses and builder. Delegate masking to core Redaction; derive deterministic redaction-summary metadata without reintroducing a second secret detector.
- [ ] Preserve Claire-compatible limitations for absent ranked context/evidence/decision refs in product-neutral wording; no resolver logic.
- [ ] Verify fixture round-trip/determinism and Ruff.
- [ ] Commit `feat: add portable context package v2`.

### Task 2: Product-neutral Required Reads Resolver

**Files:**
- Create: `src/agent_brain/context/required_reads.py`
- Test: `tests/context/test_required_reads.py`
- Create: `tests/fixtures/context/required_reads_profile.neutral.v1.json`

**Interfaces:**
- Produces:
  - `RequiredRead(path: str, priority: str, reason: str, source_ref: str | None = None, available: bool = False, warning: str | None = None)`
  - `RequiredReadRule(path: str, priority: str, reason: str, source_ref: str | None = None, keywords: tuple[str, ...] = (), operation_modes: tuple[str, ...] = ())`
  - `RequiredReadsProfile(minimum: tuple[RequiredReadRule, ...], conditional: tuple[RequiredReadRule, ...] = ())`
  - `resolve_required_reads(*, profile: RequiredReadsProfile, task_scope: str, target_issue: str | None = None, target_paths: tuple[str, ...] = (), target_symbols: tuple[str, ...] = (), target_concepts: tuple[str, ...] = (), operation_mode: str, available_paths: frozenset[str] | None = None) -> tuple[RequiredRead, ...]`

- [ ] Write RED tests characterizing the generic portion of Claire `test_context_required_reads.py`: minimum reads always present, keyword/mode conditional reads, dedupe by highest priority, stable ordering and required output fields.
- [ ] Add RED safety tests for blank/absolute/UNC/drive-letter/`..` paths. Unsafe paths stay in evidence as `available=False` with warning and never escape into filesystem access.
- [ ] Add RED test proving no built-in Claire paths or domain keywords exist; all concrete catalogs come from the injected profile fixture.
- [ ] Run focused tests; expected RED.
- [ ] Implement pure deterministic resolution with caller-supplied availability evidence only; no filesystem reads in the core resolver.
- [ ] Verify fixture and Ruff.
- [ ] Commit `feat: add required reads profile resolver`.

### Task 3: Self-Explanation on Shared Evidence Contracts

**Files:**
- Create: `src/agent_brain/context/explanation.py`
- Test: `tests/context/test_explanation.py`

**Interfaces:**
- Consumes: `EvidenceRef`, `ClaimRef`.
- Produces:
  - `SelfExplanationInput(explanation_type: str, summary: str, reasons: tuple[str, ...], evidence_refs: tuple[EvidenceRef, ...], required_next_step: str, confidence: float | None = None, scope_context: str | None = None, graph_path: tuple[str, ...] = (), uncertainties: tuple[str, ...] = (), claim_refs: tuple[ClaimRef, ...] = (), related_refs: tuple[str, ...] = (), recommended_next_reads: tuple[str, ...] = (), guardrails: tuple[str, ...] = ())`
  - `SelfExplanation(...).to_dict()`
  - `build_self_explanation(input: SelfExplanationInput) -> SelfExplanation`
  - `supported_explanation_types() -> frozenset[str]`

- [ ] Write RED tests for Claire's nine explanation types, required summary/reasons/evidence/next-step, confidence bounds, always-present graph path/uncertainties and low-confidence/weak-evidence uncertainty inference.
- [ ] Replace Claire-specific guardrail assertions with generic, injected guardrails plus a minimal non-authorizing default statement.
- [ ] Add RED tests proving output serializes the actual #15 `EvidenceRef`/`ClaimRef` payloads and exposes no Trust/Resolver authority.
- [ ] Run focused tests; expected RED.
- [ ] Implement side-effect-free builder with no DB/MCP/runtime dependency.
- [ ] Verify Ruff and focused tests.
- [ ] Commit `feat: add context self explanation core`.

### Task 4: Generic Validation Plan and Briefing Envelope

**Files:**
- Create: `src/agent_brain/context/validation.py`
- Create: `src/agent_brain/context/briefing.py`
- Test: `tests/context/test_validation.py`
- Test: `tests/context/test_briefing.py`
- Create: `tests/fixtures/context/briefing.neutral.v1.json`

**Interfaces:**
- Consumes: `ContextPackage`, `RequiredRead`, `EvidenceRef`, `PolicyHook`, `PolicyContext`, canonical hashing.
- Produces:
  - `ValidationPlanInput(impact_id: str, impact_level: str = "low", confidence: str = "low", required_checks: tuple[str, ...] = (), suggested_tests: tuple[str, ...] = (), docs_to_review: tuple[str, ...] = (), evidence_to_collect: tuple[str, ...] = (), commands_to_consider: tuple[str, ...] = (), blocking_preconditions: tuple[str, ...] = (), stop_conditions: tuple[str, ...] = (), manual_review_needed: bool = False)`
  - `ValidationPlan(...).to_dict()` and `build_validation_plan(...)`
  - `BriefingRequest(task_id: str, task_scope: str, target_issue: str | None, requested_depth: str, operation_mode: str, target_paths: tuple[str, ...] = (), target_symbols: tuple[str, ...] = (), target_concepts: tuple[str, ...] = (), risk_level: str = "medium")`
  - `BriefingEnvelope(...).to_dict()`
  - `build_briefing(request: BriefingRequest, *, context_package: ContextPackage | None, required_reads: tuple[RequiredRead, ...] = (), evidence_refs: tuple[EvidenceRef, ...] = (), validation_plan: ValidationPlan | None = None, guardrails: tuple[str, ...] = (), stop_conditions: tuple[str, ...] = (), unresolved_questions: tuple[str, ...] = (), policy_hook: PolicyHook | None = None) -> BriefingEnvelope`

- [ ] Write Validation RED tests for deterministic plan ID, propagation of blocking preconditions/stop conditions, manual-review fail-closed behavior, stable tuple/list serialization and commands-as-suggestions-only semantics.
- [ ] Do **not** port Claire's hard-coded `governance_touched`, execution/risk/LR mappings. Add a source/vocabulary test proving those product-specific derivations are absent.
- [ ] Write Briefing RED tests from Claire briefing schema: deterministic ID, valid `quick|standard|deep`, task-scoped summary, package ref, required reads, shared EvidenceRefs, validation plan, guardrails, stop conditions, unresolved questions and approval flag.
- [ ] Add RED policy tests: absent hook grants no extra authority; hook denial sets `human_go_required=True` and appends reasons as stop conditions; hook allow does not erase caller guardrails.
- [ ] Run focused tests; expected RED.
- [ ] Implement both pure builders with canonical hashes and no runtime side effects.
- [ ] Verify neutral fixture and Ruff.
- [ ] Commit `feat: add briefing and validation core`.

### Task 5: Public Surface, Documentation and Delivery Audit

**Files:**
- Modify: `src/agent_brain/context/__init__.py`
- Create: `docs/context/README.md`
- Modify: `README.md`
- Modify: `docs/START_HIER.md`
- Modify: `docs/DEVELOPMENT.md`
- Modify: this plan to close completion boxes before merge.

**Interfaces:**
- Produces the stable public imports for Slice #6 only; no CLI/MCP surface.

- [ ] Export the context/package/required-reads/explanation/validation/briefing public types and builders from `agent_brain.context`.
- [ ] Document ownership and consumer direction: #6 packages/briefs existing refs; #9 later produces repository/index inputs; #7 later computes retrieval; #8 later resolves/scored evidence; Claire-specific profiles/guardrails remain adapters.
- [ ] Document parity mapping for Claire `test_context_package_v2.py`, `test_context_required_reads.py`, `test_context_self_explanation.py`, `test_context_validation_plan.py` and the four MCP briefing tests; record deferred runtime/handler behavior explicitly.
- [ ] Update navigation/status to `SLICE_4_CONTEXT_BRIEFING`; next linear slice becomes #9.
- [ ] Scan runtime code/fixtures for `Claire`, `CDB_`, `trading`, `echtgeld`, `Live-Go`, `LR-`, `surrealdb-local`, concrete Claire paths and MCP assumptions; runtime/fixture leakage fails the slice. Historical source names may appear only in docs/plan parity references.
- [ ] Confirm `pyproject.toml` runtime dependencies remain unchanged.
- [ ] Run full CI on Python 3.12 / 3.13 / 3.14.
- [ ] Review complete PR diff, comments/reviews/threads and exact-head/base before merge; fix only #6-scope findings.
- [ ] Squash-merge with exact-head lease.
- [ ] Live-verify main SHA, PR merged state, Issue #6 close and post-merge CI.
- [ ] Comment delivery evidence on #6 and Epic #2; use `DONE_MERGED_CLOSED` only after every live gate passes.
