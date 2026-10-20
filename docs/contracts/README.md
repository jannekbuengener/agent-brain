# Gemeinsame Contracts — Slice 3

**Status:** `SLICE_3_SHARED_CONTRACTS`  
**Issue:** [#15 — Shared Source / Index / Evidence Contracts](https://github.com/jannekbuengener/agent-brain/issues/15)

## Zweck

Diese Schicht definiert die gemeinsamen, produktneutralen Datenverträge, auf denen Context Package, Repository Ingestion, Retrieval, Evidence Resolution und der spätere State-Handoff aufbauen.

Sie ist bewusst **keine Runtime**: Die Contracts beschreiben Daten, Identität, Beziehungen und Kompatibilität. Sie führen keine Repository-Erkennung, keine Suche, kein Trust-Scoring, keine Evidence-Auflösung und keine Datenbankzugriffe aus.

## Contract-Familien

| Familie | Schema | Zweck |
|---|---|---|
| `RepositorySource` | `repository-source/v1` | stabile Identität einer Repository-Quelle mit optionaler Revision/URI |
| `RepositoryProfile` | `repository-profile/v1` | generische Include-/Exclude-/Dateityp-Grenzen für eine Repository-Quelle |
| `ArtifactRef` | `artifact-ref/v1` | stabile Artifact-Referenz mit Source-ID, Pfad, Hash und optionaler Revision |
| `IndexRecord` | `index-record/v1` | minimaler, produktneutraler Index-Record mit Artifact-Provenance |
| `GraphEdge` | `graph-edge/v1` | gerichtete strukturelle Beziehung zwischen zwei Record-IDs |
| `EvidenceRef` | `evidence-ref/v1` | Evidence-Identität und Beziehungen ohne Trust-/Resolver-Autorität |
| `ClaimRef` | `claim-ref/v1` | Claim-Identität und Beziehungen ohne Resolution-/Scoring-Logik |

Die kanonischen Versionsstrings stehen zusätzlich in `agent_brain.contracts.registry.CONTRACT_SCHEMAS`.

## Serialisierung und Kompatibilität

Alle fachlichen v1-Typen besitzen `to_dict()` / `from_dict()`. Für deterministische JSON-Ausgabe steht `serialize_contract()` bereit; es verwendet die Portable Foundation für Canonical JSON.

Für v1 gilt:

- **additiv kompatibel:** ein Producer darf optionale, unbekannte Felder ergänzen; v1-Reader ignorieren sie, solange die bestehenden Pflichtfelder ihre Bedeutung und Typen behalten.
- **breaking:** Pflichtfeld entfernen oder umbenennen, einen Feldtyp bzw. dessen Semantik inkompatibel ändern, ein bisher optionales Feld zwingend machen oder Identitätssemantik ändern.
- Breaking Changes benötigen eine neue Major-Version, zum Beispiel `/v2`.
- Falsche Contract-Familien oder nicht unterstützte Major-Versionen werden fail-closed abgelehnt.

## Producer- und Consumer-Richtung

| Slice | Rolle gegenüber diesen Contracts |
|---|---|
| #6 · Context Package / Briefing | konsumiert Repository-Profile und Source-/Artifact-/Evidence-/Claim-Referenzen |
| #9 · Repository Ingestion | konsumiert Repository-Profile und produziert Source-/Artifact-/Index-/Graph-Daten |
| #16 · Knowledge Build / Seed | persistiert bzw. rekonstruiert die Build-Ausgaben auf Basis derselben Schemas |
| #7 · Retrieval | konsumiert Index-/Graph-Records; keine eigene konkurrierende Indexform |
| #8 · Evidence / Decisions / Trust | konsumiert `EvidenceRef` / `ClaimRef` und ergänzt erst dort Resolution, Trust und Scoring |
| #21 · State Migration Gate | verwendet die Schema-Grundlage für den kontrollierten State-Handoff |

Ein Consumer-Adapter darf ein konkretes `RepositoryProfile` liefern. Produkt- oder Repository-spezifische Required Reads, Trading-Grenzen und Fachpolicy gehören nicht in diese Contract-Schicht.

## Claire-Parity

Slice #15 charakterisiert die produktneutralen Teile der Claire-Baseline aus:

- `test_context_graph_contract.py` — IDs, Source-Referenzen und deterministische Struktur-Fingerprints,
- `test_db_record_evidence_contract.py` — explizite Schema-/Determinismus-Grenzen, ohne Claire-Trust-Enums oder Resolver zu übernehmen,
- `test_wave14_context_record_schemas.py` — stabile Evidence-/Claim-Referenzen und leere optionale Beziehungen.

Nicht übernommen werden Claire-spezifische Tool-Namen, Source-Priorities, Trust-Klassifikationen, Required Reads, Live-/Trading-Regeln oder DB-Runtime-Verhalten.

## Harte Grenze

Dieser Slice enthält absichtlich **nicht**:

- Repository-Ingestion oder Dateisystem-Discovery,
- Retrieval-Algorithmen,
- Context-Package-/Briefing-Runtime,
- Evidence Resolver, Trust oder Scoring,
- SurrealDB-Runtime,
- produktive Agent-Memory-Writes,
- Claire-/Trading-Policy.

Der nächste lineare Slice ist [#6 — Context Package und Briefing Core](https://github.com/jannekbuengener/agent-brain/issues/6).
