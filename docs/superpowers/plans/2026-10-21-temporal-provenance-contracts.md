# Temporal & Provenance Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the backend-neutral temporal, provenance, and supersession metadata contracts required by issue #37 without changing `EvidenceRef` or `ClaimRef`.

**Architecture:** Add three versioned contract families (`TemporalEnvelope`, `Provenance`, `ResolutionMeta`) plus nested/read-side value types (`SourceSpan`, `ResolutionState`). Keep validation/serialization JSON-safe and runtime-neutral, register/export the types, and document the #37 → #8/#11 ownership boundary.

**Tech Stack:** Python 3.12+, dataclasses, stdlib `datetime`, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-21-temporal-provenance-contract-design.md`

## Global Constraints

- `EvidenceRef` / `ClaimRef` stay reference-only and unchanged.
- No SurrealDB, Agent Memory, Spectron, Claire runtime, or new dependency.
- No memory writes, TTL/freshness resolver, conflict scoring, or persistence schema.
- `to_dict()` is JSON-safe; additive unknown v1 fields are ignored by `from_dict()`.
- incompatible schema family/major fails closed.
- `source_trust` and `confidence` are independent `[0.0, 1.0]` values.
- `resolution_state` is not stored in `ResolutionMeta`.

## Review Focus

- aware non-UTC datetimes normalize to UTC
- naive datetimes are consistently treated as UTC
- `bool` is rejected as SourceSpan offset and trust/confidence score
- `valid_until <= valid_from` fails closed
- additive unknown fields do not leak into round trips

---

### Task 1: TemporalEnvelope

**Files:** create `src/agent_brain/contracts/_validation.py`, `src/agent_brain/contracts/temporal.py`, `tests/contracts/test_temporal_contracts.py`.

**Interfaces:** `TemporalEnvelope(schema_version: str, known_at: datetime, valid_from: datetime | None = None, valid_until: datetime | None = None, system_as_of: datetime | None = None)` plus internal validation/time helpers shared by Task 2.

- [ ] Write failing tests for UTC normalization + `Z` JSON output, naive-as-UTC, validity ordering, unknown-field ignore, version rejection, `system_as_of` round-trip.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_temporal_contracts.py -q --basetemp .pytest-tmp`; expect FAIL because module is missing.
- [ ] Implement helpers and `TemporalEnvelope` using `temporal-envelope/v1`; normalize internal datetimes to naive UTC.
- [ ] Re-run the test command; expect PASS.
- [ ] Commit `feat: add temporal envelope contract`.

### Task 2: Provenance + ResolutionMeta

**Files:** create `src/agent_brain/contracts/provenance.py`, `src/agent_brain/contracts/resolution.py`, `tests/contracts/test_provenance_contracts.py`, `tests/contracts/test_resolution_contracts.py`.

**Interfaces:** `SourceSpan(start: int, end: int)`; `Provenance(schema_version, source_kind, source_ref, source_hash=None, source_span=None, source_session_id=None, source_turn_at=None, derived_from=())`; `ResolutionMeta(schema_version, supersedes_ref=None, superseded_by_ref=None, supersession_reason=None, source_trust=None, confidence=None)`; `ResolutionState` string enum with CURRENT/STALE/SUPERSEDED/UNKNOWN.

- [ ] Write failing tests for SourceSpan boundaries/bool rejection, Provenance JSON round-trip + UTC normalization, unknown-field ignore, supersession refs, score bounds/bool rejection, independent trust/confidence, exact enum values, and absence of stored `resolution_state`.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_provenance_contracts.py tests/contracts/test_resolution_contracts.py -q --basetemp .pytest-tmp`; expect FAIL because modules are missing.
- [ ] Implement immutable side-effect-free contracts; no merge/LWW or freshness logic.
- [ ] Re-run the test command; expect PASS.
- [ ] Commit `feat: add provenance and resolution metadata contracts`.

### Task 3: Registry, exports, docs, regression proof

**Files:** modify `src/agent_brain/contracts/__init__.py`, `src/agent_brain/contracts/registry.py`, `tests/contracts/test_registry.py`, `tests/contracts/test_evidence_contracts.py`, `docs/contracts/README.md`, `README.md`, `docs/START_HIER.md`.

- [ ] Extend failing registry expectation with `temporal-envelope/v1`, `provenance/v1`, `resolution-meta/v1`; assert EvidenceRef/ClaimRef still ignore temporal/trust/resolution metadata.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_registry.py tests/contracts/test_evidence_contracts.py -q --basetemp .pytest-tmp`; expect registry FAIL.
- [ ] Export/register the new contracts and document time semantics, SourceSpan offsets, trust-vs-confidence, no stored resolution state, no LWW, and #37 ownership.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests/contracts -q --basetemp .pytest-tmp`, then full `pytest -q --basetemp .pytest-tmp`, then `.\.venv\Scripts\python.exe -m ruff check .`; expect all green.
- [ ] Commit `docs: wire temporal provenance contracts into canon`.
