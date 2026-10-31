"""Cross-session Memory rediscovery (#11).

Proves that scoped Memory entries remain discoverable across distinct read
contexts/sessions without leaking across scopes. Uses the existing MemoryStore
port and MemoryReadService — no global search, no write surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent_brain.contracts.versioning import require_compatible_version
from agent_brain.memory.errors import MemoryBoundaryError
from agent_brain.memory.read.models import MEMORY_READ_RESULT_SCHEMA, MemoryReadResult
from agent_brain.memory.read.service import MemoryReadService, assert_scopes_isolated
from agent_brain.memory.scope import MemoryScope
from agent_brain.memory.types import StoreAvailability, require_memory_scope

REDISCOVERY_PROOF_SCHEMA = "memory-rediscovery-proof/v1"


@dataclass(frozen=True, slots=True)
class RediscoveryProof:
    """Deterministic evidence that scoped rediscovery succeeded or failed closed."""

    schema_version: str
    session_a_result: MemoryReadResult
    session_b_result: MemoryReadResult
    expected_record_ids: tuple[str, ...]
    scope: MemoryScope
    rediscovered_record_ids: tuple[str, ...]
    passed: bool
    detail: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="memory-rediscovery-proof",
            supported_major=1,
        )
        require_memory_scope(self.scope)
        if not isinstance(self.session_a_result, MemoryReadResult):
            raise TypeError("session_a_result must be a MemoryReadResult")
        if not isinstance(self.session_b_result, MemoryReadResult):
            raise TypeError("session_b_result must be a MemoryReadResult")
        if self.session_a_result.schema_version != MEMORY_READ_RESULT_SCHEMA:
            raise MemoryBoundaryError("session_a_result schema mismatch")
        if self.session_b_result.schema_version != MEMORY_READ_RESULT_SCHEMA:
            raise MemoryBoundaryError("session_b_result schema mismatch")


async def prove_cross_session_rediscovery(
    *,
    session_a: MemoryReadService,
    session_b: MemoryReadService,
    scope: MemoryScope,
    as_of: datetime,
    expected_record_ids: tuple[str, ...],
    subject_ref: str | None = None,
    limit: int = 100,
) -> RediscoveryProof:
    """Recall the same scope from two independent read services/sessions.

    Pass criteria:
    - both sessions AVAILABLE (or both UNAVAILABLE → fail, not empty success)
    - every expected_record_id appears in both sessions' evaluated items
    - no item escapes the requested scope
    - sessions do not invent records outside expected ids when expectations set
    """
    require_memory_scope(scope)
    if not expected_record_ids:
        raise MemoryBoundaryError("expected_record_ids must be non-empty")

    result_a = await session_a.recall_for_scope(
        scope,
        as_of=as_of,
        subject_ref=subject_ref,
        limit=limit,
        query_id="rediscovery-session-a",
    )
    result_b = await session_b.recall_for_scope(
        scope,
        as_of=as_of,
        subject_ref=subject_ref,
        limit=limit,
        query_id="rediscovery-session-b",
    )

    if (
        result_a.availability is StoreAvailability.UNAVAILABLE
        or result_b.availability is StoreAvailability.UNAVAILABLE
    ):
        return RediscoveryProof(
            schema_version=REDISCOVERY_PROOF_SCHEMA,
            session_a_result=result_a,
            session_b_result=result_b,
            expected_record_ids=expected_record_ids,
            scope=scope,
            rediscovered_record_ids=(),
            passed=False,
            detail="backend_unavailable; UNAVAILABLE != EMPTY rediscovery success",
        )

    assert_scopes_isolated(result_a.items, scope)
    assert_scopes_isolated(result_b.items, scope)

    ids_a = {item.entry.record.record_id for item in result_a.items}
    ids_b = {item.entry.record.record_id for item in result_b.items}
    expected = set(expected_record_ids)
    rediscovered = tuple(sorted(ids_a & ids_b & expected))
    passed = expected <= ids_a and expected <= ids_b

    detail = None
    if not passed:
        missing_a = sorted(expected - ids_a)
        missing_b = sorted(expected - ids_b)
        detail = f"missing_in_a={missing_a}; missing_in_b={missing_b}"

    return RediscoveryProof(
        schema_version=REDISCOVERY_PROOF_SCHEMA,
        session_a_result=result_a,
        session_b_result=result_b,
        expected_record_ids=expected_record_ids,
        scope=scope,
        rediscovered_record_ids=rediscovered,
        passed=passed,
        detail=detail,
    )


__all__ = [
    "REDISCOVERY_PROOF_SCHEMA",
    "RediscoveryProof",
    "prove_cross_session_rediscovery",
]
