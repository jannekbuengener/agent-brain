# Portable Foundation

Die Portable Foundation ist die kleinste produktneutrale technische Basis von Agent Brain. Sie enthält nur Bausteine, die spätere Contracts und Module benötigen, ohne Repository-, Evidence-, Retrieval-, Datenbank- oder Produktlogik vorwegzunehmen.

## Enthaltene Bausteine

| Modul | Zweck |
|---|---|
| `agent_brain.core.time` | injizierbare UTC-Zeit für deterministische Tests und Abläufe |
| `agent_brain.core.canonical` | kanonisches JSON und deterministisches SHA-256-Hashing |
| `agent_brain.core.identity` | kleine, domänenneutrale Identitäts- und Provenance-Primitiven |
| `agent_brain.core.source_priority` | vom Consumer injizierte Quellpriorität ohne fest eingebaute Produktnamen |
| `agent_brain.core.policy` | Schnittstelle für externe Policy-Entscheidungen, ohne Produktpolicy im Core |
| `agent_brain.core.redaction` | deterministische Maskierung sensibler Ausgaben und restriktive lokale Secret-Sidecars |

## Determinismus

Das Canonical-JSON-Verhalten wurde gegen die Claire-Extraktionsbaseline `84b5e05765fcde402a2565aa37fd42081ee95355` charakterisiert. Beibehalten werden insbesondere:

- lexikografisch sortierte JSON-Schlüssel,
- kompakte JSON-Separatoren,
- `None`-Werte werden aus Dictionaries entfernt, in Listen aber als `null` erhalten,
- `NaN` und unendliche Float-Werte werden zu `None`,
- normale Floats werden auf zehn Dezimalstellen gerundet,
- `-0.0` wird als `0.0` normalisiert,
- Hashes entstehen als SHA-256 über die UTF-8-Bytes des kanonischen JSON.

Die Claire-Dateien sind dabei historische Charakterisierungsquellen. Agent Brain importiert oder benötigt Claire nicht zur Laufzeit.

## Zeit

`FixedClock` und der injizierbare Default-Clock-Pfad ermöglichen reproduzierbare Tests ohne versteckten Wall-Clock-Zugriff. `SystemClock` liefert wie die charakterisierte Ausgangsbasis einen naiven UTC-`datetime`.

## Policy und Source Priority

Die Foundation kennt keine konkrete Produktpolicy und keine fest verdrahtete Wahrheitshierarchie. Ein Consumer liefert seine Source-Reihenfolge über `SourcePriority` und seine Policy über eine Implementierung von `PolicyHook` selbst.

Dadurch kann ein späterer Adapter strengere Regeln hinzufügen, ohne den generischen Core zu forken.

## Harte Grenze zu Slice 3

Diese Foundation definiert ausdrücklich **nicht**:

- `RepositorySource`,
- `RepositoryProfile`,
- `EvidenceRef`,
- `ClaimRef`,
- Index-/Graph-Records,
- Retrieval- oder Context-Package-Verhalten.

Diese gemeinsamen Domain-Contracts gehören in [#15 — Shared Contracts](https://github.com/jannekbuengener/agent-brain/issues/15).

## Validierung

Die Foundation wird zusammen mit dem Repository auf Python 3.12, 3.13 und 3.14 geprüft:

```bash
python -m ruff check .
python -m pytest -q
```

Die Tests unter `tests/core/` schützen die produktneutralen Foundation-Verträge und die charakterisierten deterministischen Erwartungen.
