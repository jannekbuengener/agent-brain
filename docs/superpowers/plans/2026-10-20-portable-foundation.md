# Portable Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slice #5 liefert die kleinsten produktneutralen Foundation-Bausteine, auf denen #15 gemeinsame Contracts definieren kann.

**Architecture:** `agent_brain.core` erhält kleine, voneinander getrennte Module für Zeit, Canonical JSON/Hashing, Identität/Provenance, Source-Priority, Policy-Hooks und Redaction. Claire-Verhalten wird nur dort übernommen, wo der Extraction Canon oder bestehende Tests einen produktneutralen Contract belegen; Claire-Namen, Trading-Policy, Repository-/Evidence-Contracts und Runtime-Verhalten bleiben draußen.

**Tech Stack:** Python >=3.12, Standardbibliothek, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-20-agent-brain-extraction-design.md`

## Global Constraints

- Keine Imports aus `Claire_de_Binare` oder `core.*`.
- Keine konkreten `RepositorySource`, `RepositoryProfile`, `EvidenceRef` oder `ClaimRef` aus #15 vorziehen.
- Kein Retrieval, Context Package, DB-Runtime oder produktiver Memory-Write-Pfad.
- Keine Claire-/CDB-/Trading-/Live-Go-spezifischen Namen oder Env-Variablen im generischen Foundation-Code.
- Keine neuen Runtime-Dependencies.
- Canonical-JSON-Verhalten orientiert sich an Claire-Baseline `84b5e05765fcde402a2565aa37fd42081ee95355`.

## Review Focus

- NaN/Inf, `None` und `-0.0` müssen beim Canonical JSON exakt deterministisch bleiben.
- Clock-Injektion darf keinen versteckten Wall-Clock-Zugriff in deterministischen Tests benötigen.
- Source-Priority darf keine eingebauten Claire-Quellnamen besitzen und muss Duplikate ablehnen.
- Policy-Hooks bleiben reine Schnittstelle ohne Claire-Produktentscheidungen.
- Redaction darf sensible Key-/Text-Werte maskieren, ohne SurrealDB- oder Claire-Namen vorauszusetzen.

---

### Task 1: Claire-Verträge charakterisieren

**Files:**
- Create: `tests/core/test_time.py`
- Create: `tests/core/test_canonical.py`
- Create: `tests/core/test_redaction.py`

**Interfaces:**
- Consumes: Claire `core/utils/clock.py`, `core/replay/canonical_json.py`, `tools/surrealdb/sensitive_output.py` nur als Referenz.
- Produces: konkrete produktneutrale Erwartungen für Foundation-Implementierung.

- [ ] Tests zuerst anlegen.
- [ ] CI/pytest ausführen und RED wegen fehlender Foundation-Module belegen.

### Task 2: Zeit, Canonical JSON und Redaction portabel implementieren

**Files:**
- Create: `src/agent_brain/core/time.py`
- Create: `src/agent_brain/core/canonical.py`
- Create: `src/agent_brain/core/redaction.py`

**Interfaces:**
- Produces: `Clock`, `SystemClock`, `FixedClock`, `get_default_clock`, `set_default_clock`, `utcnow`; `canonical_json_dumps`, `sha256_hex`, `canonical_hash`; produktneutrale Redaction-Helper.

- [ ] Minimal implementieren.
- [ ] Fokussierte Tests auf GREEN bringen.

### Task 3: Identität, Provenance, Source-Priority und Policy-Hooks

**Files:**
- Create: `tests/core/test_foundation_types.py`
- Create: `src/agent_brain/core/identity.py`
- Create: `src/agent_brain/core/source_priority.py`
- Create: `src/agent_brain/core/policy.py`
- Modify: `src/agent_brain/core/__init__.py`

**Interfaces:**
- Produces: generische `StableIdentity`, `ProvenanceStamp`, `SourcePriority`, `PolicyContext`, `PolicyDecision`, `PolicyHook`.
- Does not produce: Repository-/Index-/Evidence-Domaincontracts aus #15.

- [ ] Tests zuerst anlegen und RED belegen.
- [ ] Minimal implementieren und GREEN belegen.

### Task 4: Doku, Scope-Audit und Abschlussvalidation

**Files:**
- Create: `docs/foundation/README.md`
- Modify: `README.md`
- Modify: `docs/START_HIER.md`

- [ ] Foundation-Grenzen und Claire-Baseline dokumentieren.
- [ ] Vollständige Ruff-/pytest-CI auf Python 3.12/3.13/3.14 prüfen.
- [ ] Diff gegen `main` auf #5-Scope prüfen.
- [ ] PR mergen und Issue #5 nur nach Live-Verifikation schließen.
