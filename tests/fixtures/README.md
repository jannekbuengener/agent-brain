# Fixture-Konvention

Statische Fixtures in diesem Verzeichnis müssen:

1. produktneutral sein oder ihre Herkunft ausdrücklich kennzeichnen,
2. klein und deterministisch sein,
3. keine Secrets, Live-/Trading-State oder produktive Memory-Writes enthalten,
4. den Slice nennen, dessen Contract sie schützen.

Slice 1 legt nur die Konvention fest; fachliche Claire-Fixtures werden hier noch nicht kopiert.
