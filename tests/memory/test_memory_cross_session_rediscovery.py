"""Cross-session Memory rediscovery (#11)."""

from __future__ import annotations

import asyncio

from agent_brain.memory.in_memory import InMemoryMemoryStore
from agent_brain.memory.read import (
    MemoryEntryCatalog,
    MemoryReadService,
    prove_cross_session_rediscovery,
)
from tests.memory.helpers_read import AS_OF, make_entry, tenant_scope


def test_cross_session_rediscovery_reproducible() -> None:
    entry = make_entry(record_id="mem-rediscover", session_id="writer-session")
    records = (entry.record,)
    catalog = MemoryEntryCatalog((entry,))

    # Two independent read contexts sharing the same underlying fixture store
    # content (simulating durable backend) but separate service instances.
    store_a = InMemoryMemoryStore(records=records)
    store_b = InMemoryMemoryStore(records=records)
    session_a = MemoryReadService(store=store_a, catalog=catalog)
    session_b = MemoryReadService(store=store_b, catalog=catalog)

    proof = asyncio.run(
        prove_cross_session_rediscovery(
            session_a=session_a,
            session_b=session_b,
            scope=tenant_scope(),
            as_of=AS_OF,
            expected_record_ids=("mem-rediscover",),
            subject_ref="subject-1",
        )
    )
    assert proof.passed is True
    assert proof.rediscovered_record_ids == ("mem-rediscover",)
    # Freshness re-evaluated independently in both sessions.
    assert len(proof.session_a_result.items) == 1
    assert len(proof.session_b_result.items) == 1
    assert (
        proof.session_a_result.items[0].resolution_state
        == proof.session_b_result.items[0].resolution_state
    )


def test_rediscovery_respects_scope_no_cross_tenant_leak() -> None:
    keep = make_entry(record_id="mem-keep", scope=tenant_scope("tenant-a"))
    other = make_entry(record_id="mem-other", scope=tenant_scope("tenant-b"))
    catalog = MemoryEntryCatalog((keep, other))
    records = (keep.record, other.record)
    session_a = MemoryReadService(
        store=InMemoryMemoryStore(records=records), catalog=catalog
    )
    session_b = MemoryReadService(
        store=InMemoryMemoryStore(records=records), catalog=catalog
    )
    proof = asyncio.run(
        prove_cross_session_rediscovery(
            session_a=session_a,
            session_b=session_b,
            scope=tenant_scope("tenant-a"),
            as_of=AS_OF,
            expected_record_ids=("mem-keep",),
            subject_ref="subject-1",
        )
    )
    assert proof.passed is True
    for result in (proof.session_a_result, proof.session_b_result):
        ids = {item.entry.record.record_id for item in result.items}
        assert ids == {"mem-keep"}
        assert "mem-other" not in ids


def test_deterministic_repeated_recall() -> None:
    entry = make_entry(record_id="mem-det")
    service = MemoryReadService(
        store=InMemoryMemoryStore(records=(entry.record,)),
        catalog=MemoryEntryCatalog((entry,)),
    )
    first = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    second = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    assert [i.entry.record.record_id for i in first.items] == [
        i.entry.record.record_id for i in second.items
    ]
    assert [i.resolution_state for i in first.items] == [
        i.resolution_state for i in second.items
    ]
    assert [i.reason_codes for i in first.items] == [i.reason_codes for i in second.items]
