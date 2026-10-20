# Agent Brain — Datenflüsse

Diese Seite zeigt die wichtigsten Zusammenhänge als Mermaid-Diagramme. Ziel ist nicht technische Vollständigkeit, sondern schnelle Orientierung für den Operator.

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
    GATE -->|"ja"| PROV["Quelle & Provenance binden"]
    PROV --> META["Scope · TTL · Confidence · Zeitstempel"]
    META --> STORE[("Memory Store")]

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

**Wichtig:** Memory ist Wiederfindehilfe, keine Autorität. Ohne Quelle, Scope, TTL und Confidence gehört eine Information nicht in das dauerhafte Brain-Memory.

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
        S0["0 · Ownership & Contracts"]
        S1["1 · Agent-Brain Scaffold"]
        S2["2 · Portable Foundation"]
        S3["3 · Context / Briefing"]
        S4["4 · Retrieval"]
        S5["5 · Evidence / Decisions / Trust"]
        S6["6 · Repo Ingestion & Connectors"]
        S7["7 · SurrealDB Read Runtime"]
        S8["8 · Memory Read Side"]
        S9["9 · CLI / Protocol Surface"]
        S10["10 · Claire Cutover + Genericity Proof"]

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
