"""#40 evaluation gates — fixture/gold validation, native run, AM block, coupling."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from tests.benchmark.agent_memory_issue40.agent_memory_backend import (
    BLOCK_REASON,
    COMPATIBILITY,
    AgentMemoryBenchmarkBackend,
)
from tests.benchmark.agent_memory_issue40.loaders import (
    gold_by_query,
    load_fixtures,
    load_gold,
    load_queries,
)
from tests.benchmark.agent_memory_issue40.metrics import (
    mrr,
    ndcg_at_k,
    recall_at_k,
    top_k_overlap,
)
from tests.benchmark.agent_memory_issue40.native_backend import NativeBenchmarkBackend
from tests.benchmark.agent_memory_issue40.runner import (
    _core_coupling_imports,
    decide,
    run_benchmark,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_fixture_categories_cover_f1_to_f10() -> None:
    fixtures, digest = load_fixtures()
    assert digest
    ids = {item["fixture_id"] for item in fixtures["fixtures"]}
    assert ids == {f"F{i}" for i in range(1, 11)}


def test_gold_covers_every_query_and_is_independent() -> None:
    queries, _ = load_queries()
    gold, _ = load_gold()
    qids = {q["query_id"] for q in queries["queries"]}
    gids = {c["query_id"] for c in gold["cases"]}
    assert qids == gids
    assert "not generated from either backend" in gold["authority"].lower()


def test_metrics_helpers_deterministic() -> None:
    ranked = ["a", "b", "c"]
    assert recall_at_k(ranked, ["a"], 1) == 1.0
    assert mrr(ranked, ["b"]) == 0.5
    assert ndcg_at_k(ranked, ["a", "b"], 10) > 0.0
    assert top_k_overlap([ranked, ranked, ranked], k=3) == 1.0


def test_native_scope_isolation_hard_gate() -> None:
    backend = NativeBenchmarkBackend()
    queries, _ = load_queries()
    gold = gold_by_query()
    q = next(q for q in queries["queries"] if q["query_id"] == "Q-F4-scope-adversarial")

    async def _run() -> None:
        result = await backend.execute(q)
        actual = {hit.record_id for hit in result.hits}
        assert "f4-tenant-b" not in actual
        assert set(gold[q["query_id"]]["expected_records"]).issubset(actual)

    asyncio.run(_run())


def test_native_live_state_authority() -> None:
    backend = NativeBenchmarkBackend()
    queries, _ = load_queries()
    q = next(q for q in queries["queries"] if q["query_id"] == "Q-F9-live")

    async def _run() -> None:
        result = await backend.execute(q)
        assert result.live_winner == "closed"
        assert all(not hit.admissible for hit in result.hits)

    asyncio.run(_run())


def test_native_failure_safety() -> None:
    backend = NativeBenchmarkBackend()
    queries, _ = load_queries()
    q = next(q for q in queries["queries"] if q["query_id"] == "Q-F10-failure")

    async def _run() -> None:
        result = await backend.execute(q)
        assert result.availability == "unavailable"
        assert result.hits == ()

    asyncio.run(_run())


def test_agent_memory_blocked_without_paid_dependency() -> None:
    backend = AgentMemoryBenchmarkBackend(endpoint="https://example.invalid", api_key="x")
    assert COMPATIBILITY.local_no_cost_path is False
    assert COMPATIBILITY.embedding_model == "gemini-embedding-2"

    async def _run() -> None:
        result = await backend.execute(
            {"query_id": "Q-F8-semantic", "category": "semantic", "scope": {"kind": "tenant", "tenant_id": "tenant-a"}, "as_of": "2026-04-15T00:00:00"}
        )
        assert result.status == BLOCK_REASON
        assert result.hits == ()

    asyncio.run(_run())


def test_core_coupling_zero() -> None:
    assert _core_coupling_imports() == []


def test_full_benchmark_decision_is_exactly_one_outcome() -> None:
    evidence = asyncio.run(run_benchmark(repeats=5))
    decision = evidence["decision"]["decision"]
    assert decision in {"ADOPT_ADAPTER", "REFERENCE_ONLY", "REJECT_FOR_NOW"}
    assert decision == "REJECT_FOR_NOW"
    assert evidence["environment"]["productive_writes_introduced"] is False
    assert evidence["environment"]["paid_api_invoked"] is False
    assert evidence["environment"]["source_priority_preserved"] is True
    assert evidence["aggregates"]["native"]["scope_isolation"] == 1.0
    assert evidence["aggregates"]["native"]["live_state_authority"] == 1.0
    assert evidence["aggregates"]["native"]["failure_safety"] == 1.0
    assert evidence["aggregates"]["agent_memory"]["blocked"] is True
    assert evidence["compatibility"]["evaluation_status"] == BLOCK_REASON
    # Repeatability gate on native deterministic path.
    assert evidence["aggregates"]["native"]["repeatability_topk_overlap"] >= 0.90


def test_decide_rejects_when_blocked() -> None:
    native = {
        "scope_isolation": 1.0,
        "temporal_correctness": 1.0,
        "supersession_correctness": 1.0,
        "provenance_completeness": 1.0,
        "live_state_authority": 1.0,
        "failure_safety": 1.0,
        "must_hit_recall_at_10": 1.0,
        "mrr": 1.0,
        "ndcg_at_10": 1.0,
        "repeatability_topk_overlap": 1.0,
        "latency_ms": {"p95": 1.0},
        "blocked": False,
    }
    am = {**native, "blocked": True, "scope_isolation": 0.0, "must_hit_recall_at_10": 0.0}
    out = decide(native, am, [])
    assert out["decision"] == "REJECT_FOR_NOW"


def test_evidence_files_roundtrip_schema() -> None:
    evidence = asyncio.run(run_benchmark(repeats=2))
    raw = json.dumps(evidence)
    loaded = json.loads(raw)
    assert loaded["schema_version"] == "agent-memory-issue40-evaluation/v1"
    assert loaded["authority"]["issue"] == 40
