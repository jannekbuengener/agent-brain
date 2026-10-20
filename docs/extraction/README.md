# Extraction Canon — Übersicht

Dieser Bereich ist die kanonische Planungsgrundlage für die kontrollierte Herauslösung des Agent Brain aus **Claire de Binare**.

## Warum diese Dokumente existieren

Das bestehende Context-/Agent-Brain in Claire ist kein einzelnes Modul. Es besteht aus Domain-Logik, SurrealDB-Schema und -Adaptern, MCP-Oberflächen, Claire-spezifischer Policy, Operator-Ansichten und einer großen Regressionstestfläche.

Slice 0 / Issue [#3](https://github.com/jannekbuengener/agent-brain/issues/3) trennt diese Flächen deshalb vor der ersten Code-Migration in vier Entscheidungen:

- `MOVE` — generischer Brain-Baustein; wird nach Agent Brain extrahiert.
- `ADAPTER` — Prinzip ist generisch, konkrete Claire-Regeln bleiben als Claire-Profil/Adapter außerhalb des Brain-Kerns.
- `STAY` — bleibt in Claire, weil es Produkt-/Operator- oder Trading-spezifisch ist.
- `DEFER` — bewusst nicht Bestandteil der ersten Extraktionsphase.

## Dokumente

1. [Komponenten-Ownership](COMPONENT_OWNERSHIP.md) — welche Code-, MCP-, Config- und Dokumentationsflächen wohin gehören.
2. [State-Transition](STATE_TRANSITION.md) — was mit bestehendem SurrealDB-/Context-State geschieht.
3. [Parity-Gates](PARITY_GATES.md) — welche Claire-Tests welchen späteren Slice absichern.
4. [Slice-0-Closeout](SLICE_0_EXTRACTION_CANON.md) — Ergebnis, offene Gates und Folgeabhängigkeiten.
5. [`contracts/extraction/claire_extraction_inventory.v1.json`](../../contracts/extraction/claire_extraction_inventory.v1.json) — maschinenlesbare Kurzfassung.

## Live-Baseline des Audits

- Claire Source Repo: `jannekbuengener/Claire_de_Binare`
- geprüfter Claire-Stand: `main` / `84b5e05765fcde402a2565aa37fd42081ee95355`
- Working Tree bei Audit: sauber
- konkurrierender Context-Brain-Extraction-PR: keiner gefunden
- Agent-Brain Roadmap: Epic [#2](https://github.com/jannekbuengener/agent-brain/issues/2)
- Agent-Brain Baseline vor diesem Slice: `main` / `7c855eec782550327014177086bdb484353665db`

## Brain Evidence dieses Audits

`brain_source=repo-only`, `brain_status=not-used`.

Der Context-Briefing-Preflight war verfügbar, lieferte aber nur `LOW` / `repo-only` ohne belastbare DB-/Memory-/Evidence-Records. Deshalb wurden **keine DB-backed Aussagen** daraus abgeleitet. Der Canon basiert auf GitHub Live, Repo Live, Claire-Canon-Dateien, Code, Schemas, Configs und Tests.

## Harte Grenze

Diese Dokumente autorisieren **keine** Runtime-Migration, keine produktiven Memory Writes und keine Live-/Echtgeld-Aktion. Claire bleibt für Claire-spezifische Policy und Trading-Autorität verantwortlich. GitHub/Repo Live bleiben oberste Wahrheit.