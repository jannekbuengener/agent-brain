# Issue #40 — SurrealDB Agent Memory Evaluation

**Decision:** `REJECT_FOR_NOW`

**Reason:** Fair live Agent Memory evaluation is BLOCKED_EXTERNAL_MODEL_DEPENDENCY (mandatory gemini-embedding-2 + Spectron HTTP service; no authorized local no-cost path). Hard adoption gates cannot pass. Operational dependency burden is disproportionate versus the native Agent-Brain baseline that already implements #37/#39/#10/#11 contracts.

## Authority

```text
Issue: #40
Parent: #36
Authority: NO_NEW_AUTHORITY / EXECUTE_EXISTING_#40 / PARENT_#36_REMAINS_META_OWNER / EVALUATION_ONLY
```

## Compatibility Evidence

- Package: `surrealdb-memory==1.0.0b1`
- Import: `surrealdb.memory`
- Topology: Separate SurrealDB Agent Memory / Spectron HTTP service in front of SurrealDB; clients call endpoint+api_key; no supported in-process embedded library
- Embedding: `gemini-embedding-2` (3072 dim)
- Local no-cost path: `False`
- Evaluation status: `BLOCKED_EXTERNAL_MODEL_DEPENDENCY`

## Decision Matrix

| Gate | Native | Agent Memory | Adoption Requirement |
|---|---|---|---|
| Scope isolation | 1.0 | 0.0 | Agent Memory 100% |
| Temporal correctness | 1.0 | 0.0 | 100% |
| Supersession | 1.0 | 0.0 | 100% |
| Provenance | 1.0 | 0.0 | 100% accepted facts |
| Live-state authority | 1.0 | 0.0 | 100% |
| Must-hit Recall@10 | 0.9411764705882353 | 0.23529411764705882 | >=95% + not worse than native |
| Ranking MRR | 0.9411764705882353 | 0.23529411764705882 | not worse than native |
| Ranking nDCG@10 | 0.9411764705882353 | 0.23529411764705882 | not worse than native |
| Repeatability | 1.0 | 1.0 | >=0.90 |
| Failure safety | 1.0 | 0.0 | 100% |
| P95 latency | 0.24476999951730247 | 0.000100000761449337 | AM P95 <= native P95 + 200ms OR <= 2x native |
| Core coupling | 0 | 0 | 0 Agent-Memory imports in Domain/Core |
| Operational complexity | in-process native ports + optional pinned Surreal read runtime | Spectron service + SurrealDB + object store + Gemini embeddings | material value required |

## Versions

- Agent Brain: `0.3.4`
- Main SHA: `0c024a7173be923fb4c1cca3e089c33c9a8245ff`
- Agent Memory: `surrealdb-memory==1.0.0b1`
- SurrealDB pinned digest: `sha256:65000ff205b08363b035b457f292dc0a0b1cd4212935dd5ea94073cf67adf306`
- Python: `3.14.10`

## Benchmark Hashes

- Fixtures: `d55f45d15ed2c2d43dd6cc5eaf7c564d4a68088860cb4aade90e66c09ae43268`
- Queries: `5064c1afd545bc50f3f94a5d82a4535b59e231b80179da3be080e80728b420a2`
- Gold: `3cec3ed0597912beed9c6f6d1779e1298dd4b36b1f937553eebf44a6efa5091a`
- Repeated runs: `5`

## Native Baseline Notes

- Must-hit Recall@10: `0.9411764705882353` (honest miss on F8 paraphrase; native semantic/vector ranking remains deferred)
- MRR / nDCG@10: `0.9411764705882353` / `0.9411764705882353`
- P50 / P95 ms: `0.194500000361586` / `0.24476999951730247`
- Agent Memory live status: `BLOCKED_EXTERNAL_MODEL_DEPENDENCY`

## Residual / Reevaluation Preconditions

- Official local/no-cost embedding path (or explicit authorized paid eval budget)
- Pinned disposable Spectron image digest usable in CI without unknown volumes
- Demonstrable material reduction of Agent-Brain backend complexity OR clear retrieval gain
- Proof that Live-State Authority remains 100% Agent-Brain-owned under adapter

## Reference Patterns (not runtime adoption)

- tri-temporal known/valid/system separation (already absorbed via #37)
- same-provenance supersession + cross-provenance uncertainty (reference)
- explicit scope lens / fail-closed grants (aligned with #39 MemoryScope)
- retrieval/decision/response traces as first-class memory (reference-only)

## Final

```text
NO_FAKE_PASS
NO_PRODUCTIVE_AGENT_MEMORY_WRITES
NO_NEW_AUTHORITY_EXCEPT_ADOPT_ONLY_IMPLEMENTATION_FOLLOWUP
```
