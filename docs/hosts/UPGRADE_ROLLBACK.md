# Upgrade / Rollback — Host Surfaces

Pinning and lifecycle follow [#17](../distribution/CONSUMER_CONTRACT.md). Host adapters do not invent a second versioning scheme.

## Upgrade

1. Identify current pin (`agent-brain==X.Y.Z` / tag `vX.Y.Z`).
2. Identify target immutable version.
3. Run compatibility expectations if the consumer declares public exports.
4. `python -m pip install "agent-brain==<target>"`
5. Reload host plugins / restart host.
6. Smoke: health → contract match → `cdb_context` briefing/search/required_reads/evidence.

## Rollback

1. Remember the previous good pin.
2. Stop using the failed version.
3. `python -m pip install "agent-brain==<previous>"`
4. Reload host / restart.
5. Smoke health + one real `cdb_context` call.

Forbidden: rollback via manual source-tree revert; `latest` tags; unversioned `main` pins; absolute `C:\Users\...` / `D:\...` paths as install prerequisites.
