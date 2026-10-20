# Agent Brain — Datenflüsse

Diese Seite zeigt die wichtigsten Zusammenhänge als Mermaid-Diagramme. Ziel ist schnelle Orientierung für den Operator, nicht maximale Implementierungsdetailtiefe.

**Operative Planung:** [Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2)

---

## 1. Gesamtbild: Quellen → Agent Brain → Consumer

```mermaid
flowchart LR
    subgraph Quellen["Quellen / Repositories"]
        CDB["Claire de Binare"]
        SB["Sample Brain"]
        MCP["gpt-mcp-server"]
        MORE["weitere Repos / Dokumente"]
    end

    subgraph Brain["Agent Brain"]
        ING["Repo- & Dokumenten-Ingestion"]
        BUILD["Knowledge Build / Indexe"]
        RET["Hybrid Retrieval"]
        EVI["Evidence Resolver"]
        DEC["Decision Replay"]
        MEM["Memory Read\nQuelle + TTL + Confidence"]
        TRUST["Trust & Quality"]
        BRIEF["Briefing Engine"]
        DB[("SurrealDB Read Layer")]

        ING --> BUILD --> RET
        BUILD --> DB
        DB --> RET
        MEM --> RET
        RET --> EVI
        RET --> DEC
        EVI --> TRUST
        DEC --> TRUST
        RET --> BRIEF
        TRUST --> BRIEF
    end

    subgraph Consumer["Nutzende Systeme"]
        CDBC["Claire de Binare"]
        WF["Agent Workforce"]
        AG["weitere Agenten / Tools"]
    end

    CDB -->|"Code · Doku · Decisions · Evidence"| ING
    SB -->|"Code · Doku · Patterns"| ING
    MCP -->|"Schnittstellen · Verträge"| ING
    MORE --> ING

    BRIEF -->|"Kontext · Evidence · Trust Summary"| CDBC
    BRIEF -->|"Kontextpakete"| WF
    BRIEF -->|"Briefings / Nachweise"| AG
```

**Merksatz:** Das jeweilige Repository liefert die aktuelle Wahrheit. Agent Brain strukturiert, verbindet und erklärt diese Wahrheit.

---

## 2. Laufender Auftrag: vom Auftrag zum belastbaren Ergebnis

```mermaid
flowchart LR
    A["1 · Auftrag / Anfrage"] --> B["2 · Scope & Quellen bestimmen"]
    B --> C["3 · Live-Quellen prüfen"]
    C --> D["4 · Retrieval & Kontextaufbau"]
    D --> E["5 · Evidence / Entscheidungen / Memory auflösen"]
    E --> F["6 · Trust & Quality prüfen"]
    F --> G["7 · Briefing / Ergebnis"]

    GH["GitHub live"] --> C
    REPO["Repo live"] --> C
    DOC["kanonische Dokumente"] --> D
    DB[("SurrealDB read-only")] --> D
    MEM["Memory Read"] --> E

    F --> H{"Evidence ausreichend?"}
    H -->|"ja"| G
    H -->|"teilweise"| P["PARTIAL\nEinschränkungen sichtbar"]
    H -->|"nein"| X["BLOCKED / REPO_ONLY\nkeine starke Behauptung"]

    G --> O["Output: Kontext · Nachweise · Risiken · nächster Schritt"]
    P --> O
    X --> O
```

Typische Ergebnisklassen: `DB_BACKED`, `PARTIAL`, `REPO_ONLY`, `BLOCKED`.

---

## 3. Wahrheitshierarchie

```mermaid
flowchart TD
    Q["Behauptung / benötigte Information"] --> GH["1 · GitHub Live"]
    GH -->|"nicht ausreichend"| RL["2 · Repo Live"]
    RL -->|"nicht ausreichend"| VE["3 · verifizierte Context-/DB-Evidence"]
    VE -->|"nicht ausreichend"| CD["4 · kanonische Projektdateien"]
    CD -->|"nicht ausreichend"| LE["5 · Ledger / Statusdateien"]
    LE -->|"nicht ausreichend"| ME["6 · Memory / frühere Agentenberichte"]

    GH --> T["Trust-Auswertung"]
    RL --> T
    VE --> T
    CD --> T
    LE --> T
    ME --> T
    T --> OUT["Antwort mit Quelle, Confidence und Einschränkungen"]
```

Niedrigere Ebenen dürfen höhere, aktuellere Wahrheit nicht überschreiben.

---

## 4. Zwei verschiedene Write-Klassen

Das war ein zentraler Gap im ersten Plan: **Knowledge Build** und **Agent Memory** sind nicht dasselbe.

```mermaid
flowchart TB
    SRC["Repo / Doku / Evidence"] --> ING["Ingestion"]
    ING --> BUILD["Knowledge Build"]
    BUILD --> SNAP["versionierter Knowledge-/Index-Snapshot"]
    SNAP --> SEED["kontrollierter Seed / Import"]
    SEED --> DB[("SurrealDB Knowledge Store")]
    DB --> READ["read-only Retrieval"]

    OBS["Agent-Beobachtung / Erkenntnis"] --> MGATE{"Memory Write erlaubt?"}
    MGATE -->|"in diesem Epic: nein"| DEFER["DEFER"]
    MGATE -.->|"späterer eigener Scope"| MSTORE[("Agent Memory Store")]
```

### Regel

- **Knowledge-/Index-Build-Writes:** reproduzierbare Build-Artefakte; Slice [#16](https://github.com/jannekbuengener/agent-brain/issues/16).
- **Produktive Agent-Memory-Writes:** bleiben in diesem Epic `DEFER`.
- **Memory Read:** wird in Slice [#11](https://github.com/jannekbuengener/agent-brain/issues/11) extrahiert.

---

## 5. Extraction Roadmap v2

```mermaid
flowchart LR
    S0["0 · #3\nExtraction Canon"] --> S1["1 · #4\nScaffold"]
    S1 --> S2["2 · #5\nPortable Foundation"]
    S2 --> S3["3 · #15\nShared Contracts"]
    S3 --> S4["4 · #6\nContext / Briefing"]
    S4 --> S5["5 · #9\nRepo Ingestion"]
    S5 --> S6["6 · #16\nKnowledge Build / Seed"]
    S6 --> S7["7 · #7\nRetrieval"]
    S7 --> S8["8 · #8\nEvidence / Trust"]
    S8 --> S9["9 · #10\nSurrealDB Read"]
    S9 --> S10["10 · #11\nMemory Read"]
    S10 --> S11["11 · #17\nDistribution / Versioning"]
    S11 --> S12["12 · #12\nCLI / Protocol"]
    S12 --> S13["13 · #13\nClaire Cutover"]
    S13 --> S14["14 · #18\nParity / Dual Run"]
    S14 --> S15["15 · #19\nGenericity / Cleanup"]
```

### Direkte Issue-Links

| Slice | Issue |
|---|---|
| 0 · Extraction Canon | [#3](https://github.com/jannekbuengener/agent-brain/issues/3) |
| 1 · Scaffold | [#4](https://github.com/jannekbuengener/agent-brain/issues/4) |
| 2 · Portable Foundation | [#5](https://github.com/jannekbuengener/agent-brain/issues/5) |
| 3 · Shared Contracts | [#15](https://github.com/jannekbuengener/agent-brain/issues/15) |
| 4 · Context / Briefing | [#6](https://github.com/jannekbuengener/agent-brain/issues/6) |
| 5 · Repo Ingestion | [#9](https://github.com/jannekbuengener/agent-brain/issues/9) |
| 6 · Knowledge Build / Seed | [#16](https://github.com/jannekbuengener/agent-brain/issues/16) |
| 7 · Retrieval | [#7](https://github.com/jannekbuengener/agent-brain/issues/7) |
| 8 · Evidence / Trust | [#8](https://github.com/jannekbuengener/agent-brain/issues/8) |
| 9 · SurrealDB Read | [#10](https://github.com/jannekbuengener/agent-brain/issues/10) |
| 10 · Memory Read | [#11](https://github.com/jannekbuengener/agent-brain/issues/11) |
| 11 · Distribution / Versionierung | [#17](https://github.com/jannekbuengener/agent-brain/issues/17) |
| 12 · CLI / Protocol | [#12](https://github.com/jannekbuengener/agent-brain/issues/12) |
| 13 · Claire Cutover | [#13](https://github.com/jannekbuengener/agent-brain/issues/13) |
| 14 · Parity / Dual Run | [#18](https://github.com/jannekbuengener/agent-brain/issues/18) |
| 15 · Genericity / Cleanup | [#19](https://github.com/jannekbuengener/agent-brain/issues/19) |

---

## 6. Claire-Cutover ist jetzt dreistufig

```mermaid
flowchart LR
    VERSION["#17\nVersion / Pin / Rollback Contract"] --> CLI["#12\nStandalone Surface"]
    CLI --> CUT["#13\nClaire Adapter + Consumer Cutover"]
    CUT --> DUAL["#18\nDual Run + Parity + E2E"]
    DUAL -->|"Cleanup-Go"| CLEAN["#19\nGenericity Proof + Altcode-Cleanup"]

    DUAL -->|"Parity rot"| CUT
```

**Kein Big Bang:** Cutover, Beweis und Cleanup sind getrennte Entscheidungen.

---

## 7. Persistierter Claire-State: Slice-0-Gate

Noch nicht jede bestehende Datenklasse muss automatisch migriert werden.

```mermaid
flowchart TD
    STATE["bestehende persistierte Claire-Datenklasse"] --> AUDIT{"Slice #3 / Slice 0"}
    AUDIT --> REBUILD["REBUILD_FROM_SOURCE"]
    AUDIT --> MIGRATE["MIGRATE"]
    AUDIT --> DROP["DROP_WITH_REASON"]
    AUDIT --> DEFER["DEFER"]

    MIGRATE --> FOLLOW["eigener Migrationsscope vor betroffenem Runtime-Slice"]
```

Damit wird Migration nur dort gebaut, wo sie tatsächlich nötig ist.

---

## 8. Verantwortungsgrenzen im Zielbild

```mermaid
flowchart TB
    AB["Agent Brain"]
    CDB["Claire de Binare"]
    WF["Agent Workforce"]
    GH["GitHub / jeweiliges Repo"]

    GH -->|"Live-Wahrheit"| AB
    GH -->|"Code & Produktzustand"| CDB

    AB -->|"Kontext · Retrieval · Evidence · Memory · Trust"| CDB
    AB -->|"Kontextpakete"| WF

    WF -->|"Rollen · Zuständigkeiten · Agentenführung"| CDB
    CDB -->|"Claire-spezifische Profile / Policies"| AB

    AB -. "keine Produkt- oder Live-Autorität" .-> AUTH["keine Ausführungsfreigabe"]
    WF -. "keine Repo-Wahrheit" .-> AUTH
```

### Kurzform

- **GitHub / Repo:** Was ist aktuell wahr?
- **Agent Brain:** Was muss der Agent dazu wissen und wie belastbar ist dieses Wissen?
- **Agent Workforce:** Wer soll welche Arbeit unter welchen Zuständigkeiten erledigen?
- **Claire de Binare:** Welche produkt- und trading-spezifischen Regeln gelten für Claire?

---

## 9. Gap-Status

Die ursprünglichen Gaps A–E sind in **Roadmap v2** auf Planungsebene geschlossen:

- GAP A → #15 + #9 + #16 vor Retrieval.
- GAP B → #16 Build/Seed; #10 bleibt read-only.
- GAP C → #17 Distribution/Versionierung/Pinning/Rollback.
- GAP D → #13, #18 und #19 getrennt.
- GAP E → #15 definiert `EvidenceRef`/`ClaimRef`; #8 resolvt/scored später.

Offen bleibt bewusst nur **WATCH F**: bestehender persistierter Claire-State wird in Slice #0 klassifiziert.
