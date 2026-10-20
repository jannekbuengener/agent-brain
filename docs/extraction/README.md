# Extraction Canon — Übersicht

Dieser Bereich ist die kanonische Planungsgrundlage für die kontrollierte Herauslösung des Agent Brain aus **Claire de Binare** und für die spätere Adoption weiterer Repositories.

## Warum diese Dokumente existieren

Das bestehende Context-/Agent-Brain in Claire ist kein einzelnes Modul. Es besteht aus Domain-Logik, SurrealDB-Schema und -Adaptern, MCP-Oberflächen, Claire-spezifischer Policy, Operator-Ansichten und einer großen Regressionstestfläche.

Slice 0 / Issue [#3](https://github.com/jannekbuengener/agent-brain/issues/3) trennt diese Flächen deshalb vor der ersten Code-Migration in vier Entscheidungen:

- `MOVE` — generischer Brain-Baustein; wird nach Agent Brain extrahiert.
- `ADAPTER` — Prinzip ist generisch, konkrete Claire-Regeln bleiben als Claire-Profil/Adapter außerhalb des Brain-Kerns.
- `STAY` — bleibt in Claire, weil es Produkt-/Operator- oder Trading-spezifisch ist.
- `DEFER` — bewusst nicht Bestandteil der ersten Extraktionsphase.

## Dokumente

### Extraction Canon

1. [Komponenten-Ownership](COMPONENT_OWNERSHIP.md) — welche Code-, MCP-, Config- und Dokumentationsflächen wohin gehören.
2. [State-Transition](STATE_TRANSITION.md) — was mit bestehendem SurrealDB-/Context-State geschieht.
3. [Parity-Gates](PARITY_GATES.md) — welche Claire-Tests welchen späteren Slice absichern.
4. [Slice-0-Closeout](SLICE_0_EXTRACTION_CANON.md) — Ergebnis, offene Gates und Folgeabhängigkeiten.
5. [`contracts/extraction/claire_extraction_inventory.v1.json`](../../contracts/extraction/claire_extraction_inventory.v1.json) — maschinenlesbare Kurzfassung.

### Slice #9 — Repository Ingestion / Connectors

6. [Slice-5 Source → Target Matrix](SLICE_5_SOURCE_TARGET_MATRIX.md) — welche Claire-Verhaltensbausteine nach Agent Brain gehören, generalisiert werden oder bewusst zurückbleiben.
7. [Slice-5 Acceptance / Parity / Risk Matrix](SLICE_5_ACCEPTANCE_PARITY_MATRIX.md) — jedes Acceptance Criterion mit geplanter Evidence, Claire-Parity und Negative Controls.
8. [Repository Adoption How-to](REPOSITORY_ADOPTION_HOWTO.md) — wiederverwendbare Anleitung für weitere Repositories, abgeleitet aus dem Claire-Vorgehen.
9. [Implementation Plan](../superpowers/plans/2026-10-20-repository-ingestion-connectors.md) — TDD-/Task-Schnitt für #9.

### Externe / Reuse-Referenzen

10. [Externe Referenzdokumentation](../external-docs/index.md) — ACTIVE/NEXT/REFERENCE/PARKED.
11. [SurrealDB Reference Landscape](../external-docs/surrealdb-reference-landscape.md) — lokale/öffentliche SurrealDB-Reuse- und Research-Routingregeln ohne automatische Runtime-Abhängigkeit.

## Wiederverwendbares Arbeitsmuster

Aus Claire wird nicht die konkrete Produktpolicy generalisiert, sondern die Methode:

```text
Live-State
  → Canon Audit
  → MOVE / ADAPTER / STAY / DEFER
  → State: REBUILD / MIGRATE / DROP / DEFER
  → Source → Target Matrix
  → Acceptance → Evidence / Parity / Negative Controls
  → Implementierung
  → exact-head Validation
  → Closeout + Deferred Items
```

Für jede weitere Repository-Adoption ist das [Repository Adoption How-to](REPOSITORY_ADOPTION_HOWTO.md) der Startpunkt.

## Live-Baseline des Audits

- Claire Source Repo: `jannekbuengener/Claire_de_Binare`
- geprüfter Claire-Stand: `main` / `84b5e05765fcde402a2565aa37fd42081ee95355`
- Working Tree bei Audit: sauber
- konkurrierender Context-Brain-Extraction-PR: keiner gefunden
- Agent-Brain Roadmap: Epic [#2](https://github.com/jannekbuengener/agent-brain/issues/2)
- Agent-Brain Baseline vor diesem Slice: `main` / `7c855eec782550327014177086bdb484353665db`

Für Slice #9 ist die Implementierungsbaseline `main` / `ad2067872e8af687f506a9c82b4b81b13e627e2b`.

## Brain Evidence dieses Audits

`brain_source=repo-only`, `brain_status=not-used`.

Der Context-Briefing-Preflight war verfügbar, lieferte aber nur `LOW` / `repo-only` ohne belastbare DB-/Memory-/Evidence-Records. Deshalb wurden **keine DB-backed Aussagen** daraus abgeleitet. Der Canon basiert auf GitHub Live, Repo Live, Claire-Canon-Dateien, Code, Schemas, Configs und Tests.

## Harte Grenze

Diese Dokumente autorisieren **keine** Runtime-Migration, keine produktiven Memory Writes und keine Live-/Echtgeld-Aktion. Claire bleibt für Claire-spezifische Policy und Trading-Autorität verantwortlich. GitHub/Repo Live bleiben oberste Wahrheit.
