# Distribution, Versionierung und Consumer Contract

**Status:** Slice 11 / [#17](https://github.com/jannekbuengener/agent-brain/issues/17)  
**Paket:** `agent_brain.distribution`

## Zweck

Externe Consumer — zuerst Claire de Binare in #13 — sollen eine **konkrete Agent-Brain-Version** reproduzierbar beziehen, pinnen, auf Kompatibilität prüfen, kontrolliert upgraden und bei Bedarf zurückrollen.

Dieses Slice implementiert **nicht** CLI/Protocol (#12) und **nicht** den Claire-Cutover (#13).

## Kanonisches Distributionsmodell

Genau ein Primärmechanismus:

```text
exact-package-version + matching-git-tag
```

| Fläche | Regel |
|---|---|
| Package-Version | einzige deklarative Quelle: `pyproject.toml` → `[project].version` |
| Runtime-Version | `importlib.metadata.version("agent-brain")` / `agent_brain.__version__` |
| Git-Tag | `v{version}` muss zur Package-Version passen |
| Consumer-Pin | `agent-brain==X.Y.Z` oder immutable `git+…@vX.Y.Z` / Commit-SHA |

**Verboten** als kanonischer Consumer-Pin: `main`, `master`, `HEAD`, `latest`, bewegliche Branches, unversionierte lokale Pfade.

## Schnellstart für Consumer

```bash
python -m pip install "agent-brain==0.3.3"
# oder, solange kein Index-Publish nötig ist:
python -m pip install "agent-brain @ git+https://github.com/jannekbuengener/agent-brain.git@v0.3.3"
```

Danach:

```python
import agent_brain
from agent_brain.distribution import verify_installed_version, snapshot_public_surface

assert agent_brain.__version__ == "0.3.3"
verify_installed_version("0.3.3")
surface = snapshot_public_surface()
```

Details: [CONSUMER_CONTRACT.md](CONSUMER_CONTRACT.md).

## Public Surface

Nur deklarierte Package-`__all__`-Exports der Module in
`agent_brain.distribution.surface.PUBLIC_PACKAGE_MODULES` sind compatibility-relevant.
Interne Hilfsmodule und Tests sind `INTERNAL` und dürfen ohne Major-Bump wechseln.

## Beziehung zu #12 / #13

- **#12** kann CLI/Protocol einer Package-Version zuordnen und denselben Pin-/Compat-Contract nutzen.
- **#13** kann Claire auf `agent-brain==X.Y.Z` pinnen, Smoke/Upgrade/Rollback aus diesem Contract ableiten.
