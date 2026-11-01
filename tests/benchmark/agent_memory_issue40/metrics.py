"""Deterministic retrieval / ranking / repeatability metrics for #40."""

from __future__ import annotations

import math
from collections.abc import Sequence


def recall_at_k(ranked_ids: Sequence[str], relevant: Sequence[str], k: int) -> float:
    if not relevant:
        return 1.0
    top = set(ranked_ids[:k])
    hits = sum(1 for item in relevant if item in top)
    return hits / len(relevant)


def mrr(ranked_ids: Sequence[str], relevant: Sequence[str]) -> float:
    if not relevant:
        return 1.0
    relevant_set = set(relevant)
    for index, item in enumerate(ranked_ids, start=1):
        if item in relevant_set:
            return 1.0 / index
    return 0.0


def dcg_at_k(ranked_ids: Sequence[str], relevant: Sequence[str], k: int) -> float:
    relevant_set = set(relevant)
    score = 0.0
    for index, item in enumerate(ranked_ids[:k], start=1):
        if item in relevant_set:
            score += 1.0 / math.log2(index + 1)
    return score


def ndcg_at_k(ranked_ids: Sequence[str], relevant: Sequence[str], k: int) -> float:
    if not relevant:
        return 1.0
    ideal = dcg_at_k(list(relevant)[:k], relevant, k)
    if ideal == 0.0:
        return 0.0
    return dcg_at_k(ranked_ids, relevant, k) / ideal


def top_k_overlap(runs: Sequence[Sequence[str]], k: int = 10) -> float:
    """Mean pairwise Jaccard overlap of top-k id lists across repeated runs."""
    if len(runs) < 2:
        return 1.0
    sets = [set(run[:k]) for run in runs]
    pairs = 0
    total = 0.0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            union = sets[i] | sets[j]
            inter = sets[i] & sets[j]
            total += 1.0 if not union else len(inter) / len(union)
            pairs += 1
    return 1.0 if pairs == 0 else total / pairs


def latency_percentiles(samples_ms: Sequence[float]) -> dict[str, float]:
    if not samples_ms:
        return {"p50": 0.0, "p95": 0.0, "max": 0.0, "count": 0.0}
    ordered = sorted(float(x) for x in samples_ms)

    def _pct(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * p
        low = math.floor(rank)
        high = math.ceil(rank)
        if low == high:
            return ordered[low]
        weight = rank - low
        return ordered[low] * (1 - weight) + ordered[high] * weight

    return {
        "p50": _pct(0.50),
        "p95": _pct(0.95),
        "max": ordered[-1],
        "count": float(len(ordered)),
    }


def must_hit_success(ranked_ids: Sequence[str], must_hit: Sequence[str], k: int = 10) -> bool:
    if not must_hit:
        return True
    top = set(ranked_ids[:k])
    return all(item in top for item in must_hit)
