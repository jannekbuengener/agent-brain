# Agent Brain — Datenflüsse

Diese Seite zeigt die wichtigsten Zusammenhänge als Mermaid-Diagramme. Ziel ist nicht technische Vollständigkeit, sondern schnelle Orientierung für den Operator.

**Operative Planung:** [Epic #2 — Agent Brain aus Claire de Binare extrahieren](https://github.com/jannekbuengener/agent-brain/issues/2)

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
        IDX["Graphen & Indexe"]
        RET["Hybrid Retrieval"]
        EVI["Evidence Resolver"]
        DEC["Decision Replay"]
        MEM["Memory\nQuelle + TTL + Confidence"]
        TRUST["Trust & Quality"]
        BRIEF["Briefing Engine"]
        DB[("SurrealDB Read Layer")]

        ING --> IDX --> RET
        RET --> EVI
        RET --> DEC
        DB --> RET
        MEM --> RET
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

**Merksatz:** Das jeweilige Repository liefert die aktuelle Wahrheit. Agent Brain strukturiert, verbindet und erklärt diese Wahrheit für Agenten.

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
    MEM["Memory"] --> E

    F --> H{"Evidence ausreichend?"}
    H -->|"ja"| G
    H -->|"teilweise"| P["PARTIAL / Einschränkungen sichtbar machen"]
    H -->|"nein"| X["BLOCKED / REPO_ONLY / keine starke Behauptung"]

    G --> O["Output: Kontext · Nachweise · Risiken · nächster Schritt"]
    P --> O
    X --> O
```

### Typische Ergebnisklassen

- `DB_BACKED` — relevante Aussage ist durch echte DB-/Tool-Evidence gestützt.
- `PARTIAL` — Teile sind belegt, Teile bleiben eingeschränkt oder unklar.
- `REPO_ONLY` — belastbare Repo-/GitHub-Evidence, aber keine DB-gestützte Aussage.
- `BLOCKED` — die nötige Evidence fehlt oder widerspricht sich so stark, dass keine belastbare Aussage möglich ist.

---

## 3. Wahrheit und Evidence: was gewinnt bei Widerspruch?

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

**Grundregel:** Agent Brain darf niedrigere Ebenen nicht benutzen, um eine höhere, aktuellere Wahrheit zu überschreiben.

---

## 4. Memory-Lebenszyklus

```mermaid
flowchart LR
    SRC["Beobachtung / Entscheidung / Erkenntnis"] --> GATE{"Für Memory geeignet?"}

    GATE -->|"nein"| DROP["nicht speichern"]
    GATE -->|"ja · zukünftiger Write-Scope"| PROV["Quelle & Provenance binden"]
    PROV --> META["Scope · TTL · Confidence · Zeitstempel"]
    META --> STORE[("Memory Store\nWrite aktuell DEFER")]

    STORE --> READ["späterer Recall"]
    READ --> REVAL{"gegen aktuellen Live-State revalidieren"}

    REVAL -->|"aktuell"| CURRENT["CURRENT"]
    REVAL -->|"veraltet"| STALE["STALE"]
    REVAL -->|"durch neuere Evidence ersetzt"| SUPER["SUPERSEDED"]
    REVAL -->|"nicht prüfbar"| UNKNOWN["UNKNOWN"]

    CURRENT --> RET["darf Retrieval unterstützen"]
    STALE --> WARN["nur mit Warnung / nicht als aktuelle Wahrheit"]
    SUPER --> WARN
    UNKNOWN --> WARN
```

**Wichtig:** Memory ist Wiederfindehilfe, keine Autorität. Ohne Quelle, Scope, TTL und Confidence gehört eine Information nicht in das dauerhafte Brain-Memory. Im aktuellen Extraction-Epic ist die **Read Side** enthalten; produktive Agent-Memory-Writes bleiben ausdrücklich `DEFER`.

---

## 5. Extraktion aus Claire de Binare: kontrollierter Cutover

```mermaid
flowchart LR
    subgraph Heute["HEUTE · Brain sitzt in Claire"]
        C1["tools/surrealdb"]
        C2["tools/mcp"]
        C3["Context · Evidence · Decision · Memory"]
        C4["Claire-Policy · LR · Trading-Grenzen"]
        C1 --- C3
        C2 --- C3
        C3 --- C4
    end

    subgraph Migration["ÜBERGANG · Sliceweise Extraktion"]
        S0["#3 · Slice 0\nOwnership & Contracts"]
        S1["#4 · Slice 1\nAgent-Brain Scaffold"]
        S2["#5 · Slice 2\nPortable Foundation"]
        S3["#6 · Slice 3\nContext / Briefing"]
        S4["#7 · Slice 4\nRetrieval"]
        S5["#8 · Slice 5\nEvidence / Decisions / Trust"]
        S6["#9 · Slice 6\nRepo Ingestion & Connectors"]
        S7["#10 · Slice 7\nSurrealDB Read Runtime"]
        S8["#11 · Slice 8\nMemory Read Side"]
        S9["#12 · Slice 9\nCLI / Protocol Surface"]
        S10["#13 · Slice 10\nClaire Cutover + Genericity Proof"]

        S0 --> S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8 --> S9 --> S10
    end

    subgraph Ziel["ZIEL · klare Verantwortung"]
        AB["Agent Brain\ngenerischer Brain-Kern"]
        CP["Claire de Binare\nTrading-Core + Claire-Policy"]
        AD["Claire Adapter / Repo-Profil"]
        WF["Agent Workforce"]
        OTHER["weitere Repos / Tools"]

        CP --> AD -->|"Repo-Kontext / Profil"| AB
        AB -->|"Briefings · Evidence · Trust"| CP
        AB -->|"Kontextpakete"| WF
        AB -->|"generischer Context Service"| OTHER
    end

    Heute -->|"Extraktion, kein Rewrite"| Migration
    Migration -->|"Parity bewiesen"| Ziel
```

### Direkte Issue-Links

| Slice | Issue |
|---|---|
| 0 · Extraction Canon | [#3](https://github.com/jannekbuengener/agent-brain/issues/3) |
| 1 · Scaffold | [#4](https://github.com/jannekbuengener/agent-brain/issues/4) |
| 2 · Portable Foundation | [#5](https://github.com/jannekbuengener/agent-brain/issues/5) |
| 3 · Context / Briefing | [#6](https://github.com/jannekbuengener/agent-brain/issues/6) |
| 4 · Retrieval | [#7](https://github.com/jannekbuengener/agent-brain/issues/7) |
| 5 · Evidence / Trust | [#8](https://github.com/jannekbuengener/agent-brain/issues/8) |
| 6 · Repo Ingestion | [#9](https://github.com/jannekbuengener/agent-brain/issues/9) |
| 7 · SurrealDB Read | [#10](https://github.com/jannekbuengener/agent-brain/issues/10) |
| 8 · Memory Read | [#11](https://github.com/jannekbuengener/agent-brain/issues/11) |
| 9 · CLI / Protocol | [#12](https://github.com/jannekbuengener/agent-brain/issues/12) |
| 10 · Claire Cutover | [#13](https://github.com/jannekbuengener/agent-brain/issues/13) |

### Cutover-Regel

```mermaid
flowchart LR
    OLD["bestehender Claire-Pfad"] --> CONTRACT["portablen Contract extrahieren"]
    CONTRACT --> NEW["Agent Brain implementiert Contract"]
    NEW --> TEST["Claire-Regressionen + Parity-Tests"]
    TEST -->|"grün"| CONSUME["Claire konsumiert Agent Brain"]
    CONSUME --> DUAL["Dual Run / Compatibility Layer"]
    DUAL -->|"Parity stabil"| REMOVE["alten Claire-Duplikatcode entfernen"]
    TEST -->|"nicht grün"| OLD
```

**Kein Big Bang:** Altcode wird erst entfernt, nachdem der neue Pfad dieselben relevanten Verträge und Tests erfüllt.

---

## 6. Verantwortungsgrenzen im Zielbild

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

## 7. Offene Gaps zwischen den Slices

Der aktuelle lineare Plan ist **noch nicht vollständig implementierungsreif**. Die folgenden Übergaben sind im [Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2) als `OPEN_GAP` dokumentiert.

```mermaid
flowchart TB
    S3["#6 · Context Package"] -->|"GAP E\nEvidenceRef / Claim Contract fehlt"| S5["#8 · Evidence Resolver"]

    S4["#7 · Retrieval"] -.->|"GAP A\nbenötigt Source-/Index-Contract"| S6["#9 · Repo Ingestion"]

    S6 -->|"GAP B\nwer baut / seeded den lesbaren Wissensstand?"| S7["#10 · SurrealDB Read"]

    S9["#12 · CLI / Protocol"] -->|"GAP C\nDistribution · Versionierung · Pinning · Rollback"| S10["#13 · Claire Cutover"]

    S10 --> GD["GAP D\nSlice #13 zu breit:\nCutover + Dual Run + Parity + Genericity + Cleanup"]
```

### Was vor Implementierung korrigiert werden muss

1. **GAP A:** Source-/Index-/Repo-Profile-Contract vor Retrieval stabilisieren oder Slice #9 aufteilen/vorziehen.
2. **GAP B:** Knowledge-/Index-Build-Writes sauber von produktiven Agent-Memory-Writes trennen und einen reproduzierbaren Build/Seed/Import-Pfad definieren.
3. **GAP C:** Consumer-/Release-Contract für Claire definieren — Versionierung, Pinning, Cross-Repo Contract Tests und Rollback.
4. **GAP D:** Slice #13 verkleinern, wenn Cutover-Vertrag feststeht.
5. **GAP E:** Minimalen `EvidenceRef`-/Claim-Referenzvertrag früh festlegen; Resolver/Scoring bleibt später in #8.

Diese Gap-Liste ist **kein zusätzlicher Produkt-Scope**, sondern die fehlende Verbindung zwischen bereits geplanten Verantwortungsbereichen.
