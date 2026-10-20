# Repository Adoption How-to — das Claire-Muster wiederverwenden

**Zweck:** wiederverwendbare Anleitung, um weitere Repositories kontrolliert an Agent Brain anzubinden oder vorhandene Brain-/Context-Funktionen aus einem Produktrepo zu generalisieren.  
**Referenzfall:** Claire de Binare → Agent Brain.  
**Grundsatz:** **Verstehen → Live-Wahrheit prüfen → klassifizieren → Grenzen definieren → charakterisieren → implementieren → validieren → adoptieren → closeout.**

Dieses How-to ist kein automatisches Migrationsskript. Es ist ein Arbeitsvertrag für Menschen und Agenten.

---

## 1. Warum das Claire-Muster funktioniert

Bei Claire wurden nicht einfach Dateien in ein neues Repository kopiert. Vor der Extraktion wurden mehrere Schutzschichten aufgebaut:

1. **Live-State vor Erinnerung:** GitHub-/Repo-Zustand wurde vor Planung geprüft.
2. **Canon-Audit:** aktive Contracts, Runbooks, Designs und historische Dokumente wurden getrennt.
3. **Ownership:** Komponenten wurden als `MOVE`, `ADAPTER`, `STAY` oder `DEFER` klassifiziert.
4. **State-Behandlung:** persistierter State wurde separat als `REBUILD_FROM_SOURCE`, `MIGRATE`, `DROP_WITH_REASON` oder `DEFER` behandelt.
5. **Read-only/default posture:** Kontext durfte niedrigere Evidence nicht zur neuen Wahrheit machen.
6. **Adoption-Anker:** zentrale Agent-/Policy-Dokumente wurden mit Tests auf widerspruchsfreie Contract-Anker geprüft.
7. **Parity:** vorhandene Tests wurden als Verhaltenscharakterisierung benutzt, nicht blind verschoben.
8. **Closeout:** Exit Criteria, Child-PRs/SHAs, Deferred Items und Safety Boundaries wurden vor Abschluss explizit geprüft.

Claire-Referenzen am gepinnten Extraction-Baseline-Stand:

- `docs/surrealdb/SURREALDB_PRE_PHASE2_DOCS_CANON_AUDIT.md`
- `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`
- `tests/unit/agents/test_agent_brain_adoption_contract.py`
- `docs/surrealdb/SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md`

Die konkrete Claire-Trading-/LR-Policy wird **nicht** generalisiert. Generalisiert wird die Methode.

---

# Teil A — Vor jeder Implementierung

## 2. Schritt 0: Auftrag und Zielrepo festnageln

Vor dem ersten Code-Edit muss klar sein:

- Welches Repository ist Source?
- Welches Repository ist Target/Consumer?
- Welche Funktion soll übernommen oder angebunden werden?
- Was ist der kleinste eigenständig testbare Slice?
- Welche Nachfolger hängen vom Output ab?
- Welche Autorität darf **nicht** mitwandern?

### Mindest-Output

```text
source_repo:
target_repo:
source_baseline_sha:
target_baseline_sha:
issue_or_epic:
scope:
out_of_scope:
next_consumer:
```

**No-Go:** Implementieren mit „ungefähr aktueller Main“ oder ohne gepinnte Source-Baseline.

## 3. Schritt 1: Live-Wahrheit prüfen

Priorität:

1. GitHub Live — Issues, PRs, Checks, Branches, Merge-SHAs
2. Repo Live — Code, Contracts, Tests, Manifest, Git-State
3. verifizierte Context-/DB-Evidence
4. kanonische Dokumentation
5. Ledger/Statusdateien
6. Memory/Agentenberichte

### Prüfen

- offene PRs im gleichen Scope,
- bereits gemergte oder konkurrierende Arbeit,
- Default Branch / exakte HEAD-SHA,
- relevante offene/geschlossene Issues,
- aktuelle Package-/Dependency-Baseline,
- vorhandene Tests und Fixtures.

**No-Go:** Statusdatei, Chat-Zusammenfassung oder Agentenbericht gegen aktuellen GitHub-/Repo-State bevorzugen.

## 4. Schritt 2: Canon-Audit durchführen

Claire hat gezeigt, dass eine große Dokumentationsfläche ohne Klassifizierung gefährlich wird. Deshalb jede relevante Quelle einordnen:

| Klasse | Bedeutung |
| --- | --- |
| `CANONICAL` | gegenwärtiger Contract / aktive Architektur / aktuelle Policy |
| `RUNBOOK` | aktuelle Bedien-/Operator-Anleitung |
| `DESIGN` | beschlossen oder geplant, aber nicht automatisch live |
| `HISTORICAL` | Evidence früherer Zustände; keine aktuelle Autorität |
| `REFERENCE` | hilfreiches Wissen; kein Produktcontract |

### Contradiction Matrix anlegen

Für jede relevante Abweichung:

| Aussage | Quelle | Live Evidence | Status | Aktion |
| --- | --- | --- | --- | --- |
| alter Zustand | Doc | GitHub/Repo | stale/fixed/deferred | reconcile / historical markieren |

**Regel:** Safety-kritische oder scope-bestimmende Widersprüche vor Implementierung klären. Historische Logs nicht kosmetisch umschreiben, sondern als historisch markieren.

## 5. Schritt 3: Ownership klassifizieren

Jede Source-Komponente bekommt genau eine primäre Entscheidung:

### `MOVE`

Produktneutraler Contract oder Algorithmus. Kann nach Generalisierung Target-owned werden.

### `ADAPTER`

Das Prinzip ist generisch, konkrete Pfade, Policies, Namen, Credentials, Domainregeln oder Autorität bleiben beim Consumer.

### `STAY`

Funktion gehört fachlich zum Source-Produkt und soll nicht in Agent Brain wandern.

### `DEFER`

Sinnvoll, aber nicht Bestandteil des aktuellen Slices; eigener späterer Scope nötig.

### Prüffrage

> Würde diese Regel auch für ein völlig anderes Repository gelten, ohne dass man Produktnamen austauschen muss?

Wenn nein: meistens `ADAPTER` oder `STAY`, nicht `MOVE`.

## 6. Schritt 4: Persistierten State separat klassifizieren

Code-Ownership und Datenmigration sind unterschiedliche Entscheidungen.

| Klasse | Wann verwenden |
| --- | --- |
| `REBUILD_FROM_SOURCE` | Daten sind Spiegel/Index und können deterministisch aus höherer Wahrheit neu erzeugt werden |
| `MIGRATE` | Daten sind primary, valide und würden sonst verloren gehen |
| `DROP_WITH_REASON` | ungültig, verboten, veraltet oder nicht migrationswürdig |
| `DEFER` | eigener Sicherheits-/Produkt-Scope erforderlich |

**No-Go:** Einen Datenbestand nur deshalb migrieren, weil der alte Code ihn geschrieben hat.

---

# Teil B — Repository-Ingestion / Connector-spezifisch

## 7. Schritt 5: Source-Identität sauber trennen

Mindestens diese Ebenen separat modellieren:

```text
local_path
configured_repository_identity
configured_source_uri
observed_origin_or_upstream
revision
```

Ein lokaler Ordnername oder seine Position im Workspace beweist **keine** Remote-Ownership.

### Mismatch-Regel

Wenn `observed_origin` und konfigurierte Source nicht übereinstimmen:

- beide Werte behalten,
- Limitation/Finding erzeugen,
- Source niemals still umschreiben,
- keine Remote-Autorität daraus ableiten.

Dieses Muster ist besonders wichtig in großen lokalen Reference-Landschaften.

## 8. Schritt 6: Profile statt hardcodierter Roots

Repository-spezifische Auswahl gehört in ein explizites Profil, nicht in den Core.

Ein Profil beschreibt z. B.:

- Source-ID / Repository-ID,
- Revision,
- Include-Pfade,
- Exclude-Pfade,
- erlaubte File Types,
- consumer-/repo-spezifische Metadaten.

Zusätzliche Ingestion-Policy beschreibt z. B.:

- Sensitivity-Regeln,
- Forbidden-Regeln,
- maximale Dateigröße,
- lokale Modulpräfixe,
- weitere fail-closed Scan-Grenzen.

**No-Go:** „Wenn Repo == X, dann …“ im generischen Connector-Core.

## 9. Schritt 7: Read-only und offline als Default

Repository-Ingestion darf nicht nebenbei Operator werden.

Default für einen normalen Connector-Slice:

- kein Clone,
- kein Fetch/Pull,
- kein Checkout,
- kein Reset/Clean,
- kein Source-Repo-Write,
- kein GitHub-Netzwerkcheck, sofern nicht explizit Bestandteil eines separaten Connectors,
- kein DB-Write,
- kein Memory-Write.

Lokales `git remote get-url origin` ist zulässige read-only Evidence. Remote-Reachability ist eine andere Fähigkeit und muss getrennt autorisiert werden.

## 10. Schritt 8: Path-/Content-Sicherheit vor Extraktion

Vor dem Parsen:

1. Root explizit festlegen.
2. Pfade normalisieren.
3. Absolute/`..`-/Symlink-Escapes fail-closed verhindern.
4. Exclude vor normaler Verarbeitung respektieren.
5. File-Type und Size prüfen.
6. Binary/invalid UTF-8 sauber als `skipped/limited` behandeln.
7. Forbidden-/Sensitivity-Regeln anwenden.
8. erst danach Content parsen und Records erzeugen.

**Wichtig:** Ein forbidden File darf nicht erst vollständig gelesen/gehasht und anschließend als forbidden bezeichnet werden, wenn die Policy das Lesen selbst verbietet.

## 11. Schritt 9: Determinismus schützen

Stabile Identität darf nicht von der Maschine oder Laufzeit abhängen.

Nicht in stabile Fingerprints aufnehmen:

- absolute Host-Pfade,
- Wall Clock,
- zufällige Run IDs,
- Filesystem-Iteration,
- temporäre Workspace-Namen.

Normalisieren:

- Pfade repo-relativ,
- Record-/Edge-Reihenfolge sortiert,
- Text-Line-Endings (`LF`/`CRLF`) vor Content Hashing,
- Canonical JSON/Hashing über gemeinsame Foundation.

## 12. Schritt 10: Shared Contracts wiederverwenden

Vor neuen Dataclasses immer prüfen, ob der gemeinsame Contract bereits existiert.

Für Agent-Brain Repository-Ingestion sind derzeit kanonisch:

- `RepositorySource`
- `RepositoryProfile`
- `ArtifactRef`
- `IndexRecord`
- `GraphEdge`

Neue interne Helper-Typen sind okay. Neue konkurrierende Source-/Artifact-/Index-Verträge sind es nicht.

---

# Teil C — Reuse vor Eigenbau

## 13. Schritt 11: Research-Landschaft prüfen

Vor neuer Implementierung:

1. vorhandenen Code im Source-Repo prüfen,
2. vorhandene Libraries/SDKs prüfen,
3. lokale Upstream-/Reference-Repositories prüfen, wenn verfügbar,
4. offiziellen aktuellen Upstream prüfen,
5. vorhandene Skills/MCP-/Plugin-/Agent-Fähigkeiten prüfen,
6. erst dann Eigenbau entscheiden.

### SurrealDB-Beispiel

Die vorhandene SurrealDB-Landschaft ist **Research-/Reference-System**, keine automatische Agent-Brain-Dependency. Sie eignet sich, um SDK-, Schema-, Migration-, Storage-, Agent- und Memory-Muster zu studieren.

Vor Reuse immer prüfen:

- aktueller Upstream-Status,
- Archivierung/Legacy,
- Lizenz,
- Security-Grenze,
- Wartbarkeit,
- Passung zum aktuellen Slice.

Details: [`../external-docs/surrealdb-reference-landscape.md`](../external-docs/surrealdb-reference-landscape.md).

**No-Go:** „liegt lokal, also benutzen wir es“.

---

# Teil D — Parity und Adoption

## 14. Schritt 12: Bestehende Tests als Charakterisierung lesen

Claire hat eine wichtige Regel geliefert:

> Ein alter Test ist zunächst Evidence über bestehendes Verhalten, nicht automatisch eine Datei, die in das neue Repo gehört.

Für jeden relevanten Test entscheiden:

- produktneutraler Contract → neuer Agent-Brain-Test,
- Consumer-/Produktpolicy → bleibt im Consumer,
- Cross-Repo-Parity → späterer Integrations-/Cutover-Test,
- deferred Write-/Risk-Scope → nicht in read-only Core ziehen.

### RED/GREEN-Regel

Bei Implementierung:

1. portablen erwarteten Contract als RED-Test formulieren,
2. beweisen, dass er aus dem aktuellen Target-Baseline fehlt,
3. minimal implementieren,
4. fokussiert GREEN,
5. breite relevante Suite,
6. finaler exact-head CI-Lauf.

## 15. Schritt 13: Adoption-Anker definieren

Claire hat zentrale Dokumente mit `test_agent_brain_adoption_contract.py` auf Contract-Anker geprüft. Für weitere Consumer sollte dieselbe Idee verwendet werden.

Prüfbare Anker können sein:

- Wahrheitshierarchie,
- Agent-Brain ist Context/Evidence, nicht Live-Wahrheit,
- Repo-/GitHub-first,
- read-only Default,
- Consumer-spezifische Autorität bleibt beim Consumer,
- Profile/Adapter statt Core-Hardcoding,
- dokumentierte Stop Conditions.

Das Ziel ist nicht, Prosa exakt einzufrieren. Das Ziel ist, zu verhindern, dass Agent-Entrypoints und Canon-Docs sich semantisch widersprechen.

## 16. Schritt 14: Evidence pro Acceptance Criterion festlegen

Vor Implementierung jedes AC einer späteren Evidence zuordnen:

```text
Acceptance Criterion
→ owning module
→ focused test
→ negative control
→ CI/review evidence
→ downstream consumer
```

Wenn ein AC keinen konkreten späteren Beweis hat, ist der Plan noch nicht implementierungsreif.

---

# Teil E — Closeout

## 17. Schritt 15: Vor Merge nicht nur Tests zählen

Claire Phase-2 nutzte eine Exit-Criteria-Matrix. Für jeden Slice sollte es ebenfalls eine kleine Closeout-Matrix geben.

Mindestens prüfen:

- Issue-Scope vollständig,
- keine konkurrierende/offene Arbeit übersehen,
- alle relevanten Tests grün,
- Lint/Types/Build passend zum Diff,
- Product-Neutrality / Security Negative Controls,
- keine versteckte Scope-Ausweitung,
- Docs/Runbooks passen zum implementierten Verhalten,
- Deferred/Parked/Future explizit dokumentiert,
- Reviews/Threads geklärt,
- exact PR Head geprüft,
- Merge-SHA live auf `main`,
- Post-Merge-CI grün,
- Issue erst danach schließen.

## 18. Schritt 16: Deferred ist ein Ergebnis, kein Fehler

Nicht alles muss in den aktuellen Slice.

Ein sauberer Abschluss nennt getrennt:

- `DONE` — geliefert und verifiziert,
- `DEFERRED` — sinnvoll, eigener späterer Scope,
- `PARKED` — derzeit kein aktiver Scope,
- `REJECTED` — bewusst nicht Teil der Architektur,
- `BLOCKED` — echter externer Blocker.

Das verhindert, dass spätere Agenten offene Ideen für bereits aktivierte Features halten.

---

# Go/No-Go-Check für das nächste Repository

## GO für Implementierung nur wenn

- [ ] Source- und Target-Repo live verifiziert sind.
- [ ] Source-Baseline-SHA gepinnt ist.
- [ ] konkurrierende PRs/Issues geprüft sind.
- [ ] relevante Docs als Canon/Runbook/Design/Historical/Reference klassifiziert sind.
- [ ] Contradictions mit Scope-/Safety-Auswirkung geklärt sind.
- [ ] jede relevante Komponente `MOVE/ADAPTER/STAY/DEFER` besitzt.
- [ ] persistierter State separat klassifiziert ist.
- [ ] Source→Target-Matrix existiert.
- [ ] Acceptance→Evidence-/Parity-Matrix existiert.
- [ ] Shared Contracts / vorhandener Code / Libraries / Reference-Repos geprüft sind.
- [ ] lokale, konfigurierte und observed Repository-Identität getrennt modelliert sind.
- [ ] Side-Effect-Grenzen explizit sind.
- [ ] Security-/Negative-Control-Fälle vorab benannt sind.
- [ ] downstream Consumer klar ist.
- [ ] Implementierungsplan reviewbar ist.

## NO-GO / erst klären wenn

- [ ] aktueller Source-/Target-State unklar ist,
- [ ] Canon und historische Doku nicht unterscheidbar sind,
- [ ] Produktpolicy in den generischen Core leaken würde,
- [ ] DB-/Memory-/Runtime-Writes still mitwandern würden,
- [ ] Datenmigration und Codeextraktion vermischt werden,
- [ ] Remote-/Ownership-Identität aus lokalen Ordnernamen geraten wird,
- [ ] ein AC keinen späteren Beweis hat,
- [ ] eine neue Dependency nur aus Bequemlichkeit statt nach Reuse-/Security-Prüfung eingeführt würde.

---

# Wiederverwendbare Mini-Vorlage

Für einen neuen Consumer/Source-Slice kann diese Struktur kopiert werden:

```markdown
# <Repo/System> → Agent Brain Adoption

## Live Baseline
- Source repo / SHA:
- Target repo / SHA:
- Issue/Epic:
- Open competing PRs:

## Intent
- Ziel:
- Downstream consumer:
- Out of scope:

## Canon Audit
| Source | Class | Live crosscheck | Action |
|---|---|---|---|

## Ownership
| Component | MOVE/ADAPTER/STAY/DEFER | Target | Reason |
|---|---|---|---|

## State
| Data class | REBUILD/MIGRATE/DROP/DEFER | Evidence | Reason |
|---|---|---|---|

## Identity
- local path:
- configured repository:
- configured source URI:
- observed origin:
- revision:

## Acceptance → Evidence
| AC | Test/Evidence | Negative control | Consumer |
|---|---|---|---|

## Safety / Side Effects
- network:
- filesystem writes:
- repo mutation:
- DB writes:
- memory writes:
- secret handling:

## Reuse Check
- existing source implementation:
- shared Agent-Brain contracts:
- library/upstream candidates:
- local reference repos:
- decision:

## Closeout
- final head:
- checks:
- merge SHA:
- post-merge:
- issue state:
- deferred:
```

---

## Kurzform für Agenten

Wenn du ein weiteres Repository an Agent Brain anbindest:

**Nicht zuerst schreiben. Erst beweisen, was heute wahr ist; dann Canon von Historie trennen; anschließend MOVE/ADAPTER/STAY/DEFER festlegen; Datenstate separat behandeln; Source-Identitäten nicht vermischen; vorhandene Lösungen prüfen; Acceptance und Negative Controls vor dem Code festnageln; read-only/fail-closed starten; und erst nach exact-head Validation, Merge und Post-Merge-Evidence als fertig melden.**
