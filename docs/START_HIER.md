# Start hier — Agent Brain

## Was ist Agent Brain?

Agent Brain ist das gemeinsame Kontext- und Wissenssystem für KI-Agenten. Es soll nicht selbst entscheiden, **was** ein Produkt tun darf, sondern Agenten dabei helfen, den aktuellen Zustand eines Projekts korrekt zu verstehen und ihre Aussagen mit Evidence zu belegen.

Das System wird aus dem bestehenden Context-/Agent-Brain von Claire de Binare herausgelöst und als eigenständiges Repository generalisiert.

## Die wichtigste Trennung

- **Agent Brain** besitzt generische Funktionen wie Retrieval, Evidence, Decision Replay, Memory, Trust und Repo-Kontext.
- **Claire de Binare** behält Trading-Core, Live-Readiness, Echtgeld-Grenzen und andere Claire-spezifische Policies.
- **Agent Workforce** bleibt für Rollen, Zuständigkeiten und Agentenführung verantwortlich.
- **GitHub und das jeweilige Repository bleiben die aktuelle Wahrheit.** Agent Brain liefert Kontext, nicht Autorität.

## Was Agent Brain später können soll

1. Repositories und ausgewählte Dokumente einlesen und strukturieren.
2. Code, Dokumentation, Entscheidungen und Evidence miteinander verknüpfen.
3. Relevanten Kontext für einen Auftrag gezielt abrufen.
4. Aussagen auf Quellen, Aktualität und Widersprüche prüfen.
5. frühere Entscheidungen nachvollziehbar wiedergeben.
6. begrenztes, quellengestütztes Memory über Sessions hinweg bereitstellen.
7. anderen Systemen strukturierte Briefings und Trust-Zusammenfassungen liefern.

## Was Agent Brain ausdrücklich nicht sein soll

- keine zweite Source of Truth neben GitHub oder dem Repo,
- keine Trading-Runtime,
- keine Live-/Echtgeld-Freigabeinstanz,
- kein unkontrollierter Memory-Speicher,
- kein Sammelbecken für produktspezifische Geschäftslogik,
- keine Voraussetzung für private ChatGPT-Operator-Zugänge.

## Wo sehe ich die Datenflüsse?

Die wichtigsten Abläufe sind in [DATENFLUESSE.md](DATENFLUESSE.md) als Mermaid-Diagramme dokumentiert. Diese Diagramme sind bewusst Teil der normalen Markdown-Dokumentation und können direkt in GitHub gerendert und versioniert werden.

## Aktueller Arbeitsmodus

Wir befinden uns in der **Extraction-Planung**. Vor dem ersten Code-Slice werden Eigentumsgrenzen, Kompatibilitätsstrategie, Parity-Gates und die Reihenfolge der Migration festgelegt.
