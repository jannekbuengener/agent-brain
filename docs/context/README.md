# Context Package und Briefing Core

Slice #6 besitzt den produktneutralen, side-effect-freien Kern für Context Packages, Required Reads, Self-Explanation, Validation Plans und Agent Briefings.

## Module

| Modul | Verantwortung |
|---|---|
| `agent_brain.context.package` | Baut deterministische, redigierte `context-package/v2`-Envelopes auf `ArtifactRef`, `EvidenceRef`, Source-Priority und Foundation-Hashing auf. |
| `agent_brain.context.required_reads` | Löst Required Reads aus einem injizierten Profil deterministisch auf. Der Core liest selbst keine Dateien und besitzt keinen eingebauten Produktkatalog. |
| `agent_brain.context.explanation` | Erzeugt side-effect-freie Self-Explanation-Evidence auf den gemeinsamen `EvidenceRef`-/`ClaimRef`-Verträgen. |
| `agent_brain.context.validation` | Erzeugt generische Validation Plans. Kommandos sind Vorschläge; der Plan führt nichts aus und erteilt keine Freigabe. |
| `agent_brain.context.briefing` | Baut task-scoped Briefing-Envelopes aus Package, Required Reads, Evidence und Validation. Consumer-Policy wird ausschließlich über einen optionalen `PolicyHook` injiziert. |

## Determinismus und Sicherheit

- Package-, Explanation-, Validation- und Briefing-IDs werden aus kanonisch gehashten stabilen Inhalten erzeugt.
- Wall-Clock-Felder verändern die Context-Package-Identität nicht.
- Sensitive Werte werden vor der Hash-/Package-Ausgabe über die Portable Foundation redigiert.
- Secret-only Änderungen erzeugen keinen anderen Context-Package-Hash.
- Unsafe Required-Read-Pfade werden nicht aufgelöst und als nicht verfügbar markiert.
- Policy-Denials können Stop-/Approval-Evidence erzeugen, autorisieren aber niemals selbst eine Aktion.
- `briefing_does_not_authorize_action` und `explanation_does_not_authorize_action` sind generische Nicht-Autorisierungsgrenzen.

## Ownership-Grenzen

Slice #6 **paketiert und erklärt vorhandene Referenzen**. Er übernimmt nicht die Verantwortung späterer Slices:

- #9 Repository Ingestion / Connectors erzeugt später Repository-/Artifact-/Index-Eingaben.
- #16 Knowledge Build / Seed erzeugt reproduzierbaren Knowledge-/Index-State.
- #7 Retrieval berechnet später relevante Kontexte.
- #8 Evidence / Trust löst und bewertet Evidence/Claims.
- #10 SurrealDB Read führt Datenbank-Lesezugriff ein.
- #11 Memory Read führt freigegebene Memory-Lesewege ein.
- #12 CLI / Protocol exponiert spätere Consumer-/Protocol-Oberflächen.

Nicht Teil dieses Slices sind SurrealDB-Runtime, MCP-/Protocol-Handler, Netzwerkzugriff, Retrieval-Algorithmen, Evidence-/Claim-Resolver, Trust-Scoring, produktive Memory Writes oder produktspezifische Guardrails.

## Required Reads

Der generische Core kennt nur `RequiredReadsProfile` und `RequiredReadRule`. Konkrete Pfade, Keywords und Operation Modes kommen vom Consumer-Profil. Damit bleibt der Claire-spezifische Read-Katalog außerhalb von Agent Brain.

Availability ist ebenfalls caller-supplied. `resolve_required_reads()` greift nicht selbst auf das Dateisystem zu.

## Parity-Mapping zur gepinnten Extraktionsbaseline

Die produktneutralen Regressionen charakterisieren die portable Semantik der gepinnten Claire-Baseline `84b5e05765fcde402a2565aa37fd42081ee95355`:

| Claire-Baseline | Agent-Brain-Regression |
|---|---|
| `test_context_package_v2.py` | `tests/context/test_package.py` |
| `test_context_required_reads.py` | `tests/context/test_required_reads.py` |
| `test_context_self_explanation.py` | `tests/context/test_explanation.py` |
| `test_context_validation_plan.py` | `tests/context/test_validation.py` |
| Agent-Briefing-Schema / zugehörige Briefing-Contract-Tests | `tests/context/test_briefing.py` |

Claire-spezifische Risk-, Trading-, LR-, Live-/Echtgeld- und konkrete Required-Read-Regeln werden nicht in den generischen Core übernommen. Runtime-/MCP-Handler-Parity bleibt ausdrücklich späterem Adapter-/Protocol-/Parity-Scope vorbehalten.

## Öffentliche API

Der stabile Slice-4-Einstieg ist `agent_brain.context`. Die package-level Exports werden durch `tests/context/test_public_surface.py` geschützt.

## Externe technische Referenzen

Bei Dependency-, CI-, Protocol-, DB- oder Tooling-Fragen zusätzlich [Externe Referenzdokumentation](../external-docs/index.md) lesen. `P0`/`P1` bedeuten dort aktuell durch Repo-Evidence belegte Kern-/Sekundärreferenzen; `P2` ist geparkt/reference-only und keine Aussage über vorhandene Runtime-Fähigkeiten oder Dependencies.
