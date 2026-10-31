# Agent Brain Consumer Contract (#17)

## 1. Welche Version verwende ich?

```python
import agent_brain
print(agent_brain.__version__)
```

Die deklarative Quelle ist ausschließlich `pyproject.toml` `[project].version`.
Runtime und Package-Metadaten müssen übereinstimmen (CI/Tests erzwingen das).

## 2. Wie installiere ich genau diese Version?

Kanonisch:

```text
agent-brain==<version>
```

Äquivalent immutable:

```text
agent-brain @ git+https://github.com/jannekbuengener/agent-brain.git@v<version>
```

Commit-SHA-Pins sind erlaubt, wenn die installierte Package-Version zusätzlich verifiziert wird.

Nicht kanonisch: `main`, Branches, `latest`, unversionierte lokale Checkout-Pfade.

## 3. Welche Kompatibilität ist garantiert?

| ChangeKind | Bedeutung | SemVer |
|---|---|---|
| `additive` | bestehende Public Exports/Contracts behalten Bedeutung; neue optionale Exports/Felder erlaubt | minor/patch |
| `breaking` | Public Export entfernt/umbenannt; Contract-Semantik inkompatibel; Install-Constraints schließen zuvor unterstützte Umgebungen aus | major |
| `deprecation` | Export bleibt verfügbar, Entfernung angekündigt | minor + Hinweis |
| `internal` | außerhalb der Public Surface | beliebig |

Maschinenprüfbar über:

- `snapshot_public_surface()`
- `compare_public_surfaces(baseline, candidate)`
- `evaluate_consumer_expectations(...)`

## 4. Wie erkenne ich einen Contract-Bruch?

Ein Consumer deklariert erwartete Public Exports. Fehlt einer, liefert
`evaluate_consumer_expectations` `CompatibilityVerdict.INCOMPATIBLE`.
Entfernte Public Exports in einem Surface-Diff sind ebenfalls breaking.

## 5. Upgrade

Nutze `build_upgrade_plan(current_version=..., target_version=..., compatibility=...)`.

Ablauf:

1. aktuelle Pin-Version identifizieren  
2. Zielversion identifizieren  
3. Compatibility-/Contract-Check gegen Ziel  
4. Ziel-Pin installieren  
5. Consumer-Smoke  
6. Erfolg dokumentieren  

Inkompatible Ziele werden fail-closed abgelehnt.

## 6. Rollback

Nutze `build_rollback_plan(failed_version=..., previous_version=...)`.

Ablauf:

1. letzte bekannte gute Pin-Version (bereits recorded)  
2. fehlgeschlagene Version nicht weiter nutzen  
3. vorherige exakte Pin erneut installieren  
4. Consumer-Smoke  
5. Rollback dokumentieren  

Kein manuelles Rekonstruieren eines unbekannten Workspace-Zustands.

## 7. Consumer-Smoke

Minimales neutrales Fixture:

`tests/fixtures/distribution/neutral_consumer/`

Es importiert Agent Brain, verifiziert die Pin-Version und prüft erwartete Public Exports.
Es enthält keine Claire-/Trading-Logik.

## Python-/Dependency-Grenzen

- `requires-python = ">=3.12"`
- Runtime-Dependencies: keine (Core bleibt dependency-frei)
- `dev` optional: pytest, ruff

## Out of Scope hier

- CLI / Protocol Surface → #12  
- Claire Cutover → #13  
- Dual Run / Parity → #18  
- generische Release-Automation ohne Contract-Nutzen  
