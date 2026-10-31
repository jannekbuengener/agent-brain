# Improvement Blackboard Markdown Projection — #51

**Status:** `READ_ONLY_PROJECTION_V1`  
**Issue:** [#51](https://github.com/jannekbuengener/agent-brain/issues/51)  
**Depends on:** [#46](https://github.com/jannekbuengener/agent-brain/issues/46) contracts, [#47](https://github.com/jannekbuengener/agent-brain/issues/47)/[#48](https://github.com/jannekbuengener/agent-brain/issues/48) stores, [#49](https://github.com/jannekbuengener/agent-brain/issues/49) relations, [#52](https://github.com/jannekbuengener/agent-brain/issues/52) work_refs

## Zweck

Menschenfreundliche, editorneutrale Sicht auf das Improvement Blackboard — ohne Markdown/Obsidian zur zweiten mutable Truth zu machen.

## API

```python
from datetime import UTC, datetime
from agent_brain.improvement import (
    ImprovementMarkdownProjection,
    InMemoryImprovementObservationStore,
)

store = InMemoryImprovementObservationStore()
# ... submit observations / management mutations ...

result = ImprovementMarkdownProjection().export(
    store,
    "./vault-out",
    generated_at=datetime.now(tz=UTC),  # fixed timestamp for bit-identical rebuilds
)
print(result.source_hash, result.files_written)
```

`generated_at` ist Pflichtparameter, damit Exporte bei identischem Source-State bit-identisch reproduzierbar sind.

## Vault-Layout

```text
blackboard/
  index.md
  _projection/
    meta.json          # projection_version, source_hash, generated_at
    manifest.json      # path -> content sha256 (manual-edit detection)
  improvements/
    IMP-<skill>--<root-cause>.md
  skills/
    <skill-id>.md
  repositories/
    <owner>--<repo>.md
  work/
    <repo>-issue-<n>.md
  views/
    open.md
    validated.md
    verified.md
    by-lifecycle.md
    by-priority.md
    by-skill.md
    by-repository.md
```

Dateinamen sind stabil und filesystem-sicher (`:`/`/` → `--`, Prefix `IMP-` für Improvements).

## Invarianten

1. **One-way:** Brain → Projection. Kein `import_*` / `write_back` / `sync_from_markdown`.
2. **Determinismus:** gleicher Store-State + gleiches `generated_at` → byte-identische Dateien.
3. **Source hash:** SHA-256 über kanonisch serialisierte Improvements + Observations.
4. **Manual edits:** weicht eine Datei vom letzten Manifest-Hash ab und vom neuen Export, → `ImprovementProjectionConflict` (außer `force=True`).
5. **Rebuild:** vollständiger Vault ist aus Store-State rekonstruierbar; Projection ist nicht SoT.
6. Keine `MemoryStore` / `KnowledgeStore` Writes; keine neuen Runtime-Dependencies.

## Manual Edit Policy V1

Human edits im Vault sind nicht kanonisch. Export überschreibt sie nicht still.
Ein späterer Import-Workflow (`Vault change → import candidate → validation → apply`) braucht ein eigenes Issue.
