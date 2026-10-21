# Temporal- und Provenance-Contract-Design

**Issue:** #37  
**Status:** APPROVED / IMPLEMENTATION BASELINE

## Ziel

Agent Brain erhält backend-neutrale Ergänzungsverträge für Temporalität, Provenance und Supersession/Resolution-Metadaten. `EvidenceRef` und `ClaimRef` bleiben unverändert reference-only. Keine SurrealDB-, Agent-Memory- oder Claire-Runtime-Typen werden Teil der Contracts.

## Contract-Familien

- `TemporalEnvelope` → `temporal-envelope/v1`
- `Provenance` → `provenance/v1`
- `ResolutionMeta` → `resolution-meta/v1`
- `SourceSpan` ist ein eingebetteter Value Type, keine eigene Schema-Familie.
- `ResolutionState` ist ein read-side Enum (`CURRENT`, `STALE`, `SUPERSEDED`, `UNKNOWN`), aber **kein gespeichertes Feld** von `ResolutionMeta`.

## Zeitsemantik

`TemporalEnvelope` enthält:

- `known_at`: erforderlich; wann Agent Brain den Belief registriert/akzeptiert hat.
- `valid_from`: optional; Beginn der fachlichen/realweltlichen Gültigkeit.
- `valid_until`: optional; exklusives Ende der fachlichen/realweltlichen Gültigkeit.
- `system_as_of`: optional; Storage-/Read-Snapshot-Metadatum. Es ist keine Realwelt-Gültigkeit und keine frei interpretierbare Fact-Zeit.

Zeitwerte sind UTC. Python-`datetime` ohne Zeitzone wird als UTC interpretiert; aware Datetimes werden nach UTC normalisiert. JSON-Serialisierung nutzt RFC3339/ISO-8601 mit `Z`. `valid_until` muss, wenn beide gesetzt sind, strikt nach `valid_from` liegen.

## Provenance

`Provenance` enthält mindestens:

- `source_kind`
- `source_ref`
- optional `source_hash`
- optional `source_span`
- optional `source_session_id`
- optional `source_turn_at`
- `derived_from` als geordnete Tuple stabiler Referenzen

`SourceSpan` ist 0-based, end-exclusive und bezieht sich auf Unicode-Codepoints. Es gilt `0 <= start < end`.

## Resolution / Supersession

`ResolutionMeta` enthält:

- optional `supersedes_ref`
- optional `superseded_by_ref`
- optional `supersession_reason`
- optional `source_trust` in `[0.0, 1.0]`
- optional `confidence` in `[0.0, 1.0]`

`source_trust` beschreibt Vertrauen in die Quelle; `confidence` beschreibt Sicherheit der Extraktion/Aussage. Beide sind unabhängig und dürfen nicht gegenseitig abgeleitet werden.

Der Contract führt **keine** Last-Write-Wins-Auflösung aus. Unterschiedliche Provenance-Ströme bleiben getrennt und müssen später durch #8/#11 als Conflict/Uncertainty behandelt werden. Historie bleibt über Supersession-Referenzen rekonstruierbar.

`ResolutionState` wird später von Read-/Resolver-Logik aus Temporalität, Supersession, Freshness/TTL und Revalidation abgeleitet. #37 speichert keinen `resolution_state` als Wahrheit.

## Serialisierung / Kompatibilität

Alle drei Schema-Familien besitzen `to_dict()` / `from_dict()` und folgen den bestehenden v1-Regeln:

- additive unbekannte Felder werden beim Lesen ignoriert,
- falsche Contract-Familien oder Major-Versionen failen geschlossen,
- `to_dict()` liefert JSON-sichere primitive Werte,
- keine Runtime-Abhängigkeit wird eingeführt.

## Non-Goals

- keine SurrealDB-Runtime oder Storage-Entscheidung
- keine Agent-Memory-SDK-Abhängigkeit
- keine produktiven Memory-Writes
- kein TTL-/Freshness-Resolver
- keine Conflict-/Trust-Scoring-Engine
- kein Persistenzschema
- keine Änderung an `EvidenceRef` / `ClaimRef`
