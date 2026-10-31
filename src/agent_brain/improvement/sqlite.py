"""Durable ImprovementObservationStore backed by stdlib sqlite3 (#48).

Reuses the #47 ObservationStore port. Does not touch KnowledgeStore/MemoryStore
and introduces no third-party database dependency.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import replace
from pathlib import Path

from agent_brain.contracts.improvement import (
    Improvement,
    ImprovementLifecycle,
    ImprovementObservation,
    build_improvement_id,
    derive_recurrence,
    normalize_root_cause_key,
)
from agent_brain.contracts.serialization import serialize_contract
from agent_brain.improvement.errors import (
    ImprovementIdentityAmbiguous,
    ImprovementStoreUnavailable,
    ImprovementValidationError,
    InvalidImprovementScope,
)
from agent_brain.improvement.ports import SubmitObservationResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS improvements (
    improvement_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    improvement_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload TEXT NOT NULL,
    FOREIGN KEY (improvement_id) REFERENCES improvements(improvement_id)
);
CREATE INDEX IF NOT EXISTS idx_observations_improvement
    ON observations(improvement_id);
"""


class SqliteImprovementObservationStore:
    """Process-safe append-only observation store using a SQLite file."""

    MANAGEMENT_METHODS = frozenset(
        {
            "set_priority",
            "transition_lifecycle",
            "merge_improvements",
            "link_work_item",
            "link_pull_request",
            "record_verification",
        }
    )

    def __init__(self, path: str | Path, *, available: bool = True) -> None:
        self._path = Path(path)
        self._available = available
        self._lock = threading.RLock()
        if available:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.executescript(_SCHEMA)
                conn.commit()

    def mark_unavailable(self) -> None:
        self._available = False

    def mark_available(self) -> None:
        self._available = True
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _ensure_available(self) -> None:
        if not self._available:
            raise ImprovementStoreUnavailable("improvement observation store unavailable")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def submit_observation(self, observation: ImprovementObservation) -> SubmitObservationResult:
        if not isinstance(observation, ImprovementObservation):
            raise TypeError("observation must be an ImprovementObservation")
        self._ensure_available()

        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                existing = conn.execute(
                    "SELECT payload, improvement_id FROM observations WHERE idempotency_key = ?",
                    (observation.idempotency_key,),
                ).fetchone()
                if existing is not None:
                    stored_obs = ImprovementObservation.from_dict(
                        json.loads(existing["payload"])
                    )
                    improvement = self._load_improvement(conn, existing["improvement_id"])
                    conn.execute("COMMIT")
                    return SubmitObservationResult(
                        observation=stored_obs,
                        improvement=improvement,
                        created_new_observation=False,
                        created_new_improvement=False,
                    )

                improvement_id, root_cause_key = self._resolve_identity(conn, observation)
                bound = (
                    observation
                    if observation.improvement_id == improvement_id
                    and observation.root_cause_key == root_cause_key
                    else replace(
                        observation,
                        improvement_id=improvement_id,
                        root_cause_key=root_cause_key,
                    )
                )

                current_row = conn.execute(
                    "SELECT payload FROM improvements WHERE improvement_id = ?",
                    (improvement_id,),
                ).fetchone()
                created_new_improvement = current_row is None
                if created_new_improvement:
                    improvement = self._new_improvement_from_observation(
                        bound, improvement_id, root_cause_key
                    )
                    conn.execute(
                        "INSERT INTO improvements(improvement_id, payload) VALUES (?, ?)",
                        (improvement_id, serialize_contract(improvement.to_dict())),
                    )
                else:
                    current = Improvement.from_dict(json.loads(current_row["payload"]))
                    if current.skill_id != bound.skill_id:
                        raise InvalidImprovementScope(
                            "observation skill_id does not match existing improvement"
                        )

                dup_id = conn.execute(
                    "SELECT 1 FROM observations WHERE observation_id = ?",
                    (bound.observation_id,),
                ).fetchone()
                if dup_id is not None:
                    raise ImprovementValidationError(
                        f"observation_id already exists: {bound.observation_id}"
                    )

                conn.execute(
                    "INSERT INTO observations(observation_id, improvement_id, idempotency_key, payload) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        bound.observation_id,
                        improvement_id,
                        bound.idempotency_key,
                        serialize_contract(bound.to_dict()),
                    ),
                )
                improvement = self._refresh_aggregate(conn, improvement_id)
                conn.execute("COMMIT")
                return SubmitObservationResult(
                    observation=bound,
                    improvement=improvement,
                    created_new_observation=True,
                    created_new_improvement=created_new_improvement,
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def get_improvement(self, improvement_id: str) -> Improvement | None:
        self._ensure_available()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM improvements WHERE improvement_id = ?",
                (improvement_id,),
            ).fetchone()
            if row is None:
                return None
            return Improvement.from_dict(json.loads(row["payload"]))

    def list_improvements(
        self,
        *,
        skill_id: str | None = None,
        repository_ref: str | None = None,
        lifecycle: ImprovementLifecycle | str | None = None,
    ) -> tuple[Improvement, ...]:
        self._ensure_available()
        lifecycle_filter = None if lifecycle is None else ImprovementLifecycle(lifecycle)
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM improvements").fetchall()
        items = [Improvement.from_dict(json.loads(row["payload"])) for row in rows]
        if skill_id is not None:
            items = [item for item in items if item.skill_id == skill_id]
        if repository_ref is not None:
            items = [item for item in items if repository_ref in item.repository_refs]
        if lifecycle_filter is not None:
            items = [item for item in items if item.lifecycle == lifecycle_filter]
        items.sort(key=lambda item: (item.skill_id, item.root_cause_key, item.improvement_id))
        return tuple(items)

    def list_observations(self, improvement_id: str) -> tuple[ImprovementObservation, ...]:
        self._ensure_available()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM observations WHERE improvement_id = ?",
                (improvement_id,),
            ).fetchall()
        items = [
            ImprovementObservation.from_dict(json.loads(row["payload"]))
            for row in rows
        ]
        items.sort(key=lambda item: (item.timestamp, item.observation_id))
        return tuple(items)

    def find_candidates(
        self,
        *,
        skill_id: str,
        root_cause_key: str | None = None,
        repository_ref: str | None = None,
    ) -> tuple[Improvement, ...]:
        self._ensure_available()
        if not skill_id or not str(skill_id).strip():
            raise InvalidImprovementScope("skill_id is required for candidate lookup")
        items = self.list_improvements(skill_id=skill_id, repository_ref=repository_ref)
        if root_cause_key is None:
            return items
        key = normalize_root_cause_key(root_cause_key)
        return tuple(item for item in items if item.root_cause_key == key)

    def _load_improvement(self, conn: sqlite3.Connection, improvement_id: str) -> Improvement:
        row = conn.execute(
            "SELECT payload FROM improvements WHERE improvement_id = ?",
            (improvement_id,),
        ).fetchone()
        if row is None:
            raise ImprovementValidationError(f"missing improvement aggregate: {improvement_id}")
        return Improvement.from_dict(json.loads(row["payload"]))

    def _resolve_identity(
        self,
        conn: sqlite3.Connection,
        observation: ImprovementObservation,
    ) -> tuple[str, str]:
        if observation.root_cause_key is None and observation.improvement_id is None:
            raise ImprovementIdentityAmbiguous(
                "observation requires root_cause_key or improvement_id"
            )
        if observation.root_cause_key is not None:
            root_cause_key = normalize_root_cause_key(observation.root_cause_key)
            improvement_id = build_improvement_id(
                skill_id=observation.skill_id,
                root_cause_key=root_cause_key,
            )
            if (
                observation.improvement_id is not None
                and observation.improvement_id != improvement_id
            ):
                raise InvalidImprovementScope(
                    "improvement_id does not match skill_id/root_cause_key identity"
                )
            return improvement_id, root_cause_key

        assert observation.improvement_id is not None
        row = conn.execute(
            "SELECT payload FROM improvements WHERE improvement_id = ?",
            (observation.improvement_id,),
        ).fetchone()
        if row is None:
            raise ImprovementIdentityAmbiguous(
                "improvement_id unknown and root_cause_key missing; refusing to invent identity"
            )
        existing = Improvement.from_dict(json.loads(row["payload"]))
        return existing.improvement_id, existing.root_cause_key

    def _new_improvement_from_observation(
        self,
        observation: ImprovementObservation,
        improvement_id: str,
        root_cause_key: str,
    ) -> Improvement:
        repo_refs = () if observation.repository_ref is None else (observation.repository_ref,)
        task_refs = () if observation.task_ref is None else (observation.task_ref,)
        return Improvement(
            schema_version="improvement/v1",
            improvement_id=improvement_id,
            skill_id=observation.skill_id,
            root_cause_key=root_cause_key,
            summary=observation.observation,
            recommendation=observation.recommendation,
            expected_benefit="pending-board-validation",
            lifecycle=ImprovementLifecycle.NEW,
            first_seen=observation.timestamp,
            last_seen=observation.timestamp,
            skill_version_ref=observation.skill_version_ref,
            confidence=observation.confidence,
            recurrence=0,
            repository_refs=repo_refs,
            task_refs=task_refs,
            revision=1,
        )

    def _refresh_aggregate(self, conn: sqlite3.Connection, improvement_id: str) -> Improvement:
        current = self._load_improvement(conn, improvement_id)
        rows = conn.execute(
            "SELECT payload FROM observations WHERE improvement_id = ?",
            (improvement_id,),
        ).fetchall()
        history = [
            ImprovementObservation.from_dict(json.loads(row["payload"]))
            for row in rows
        ]
        history.sort(key=lambda item: (item.timestamp, item.observation_id))
        recurrence = derive_recurrence(len(history))
        first_seen = min(item.timestamp for item in history)
        last_seen = max(item.timestamp for item in history)
        repository_refs = tuple(
            dict.fromkeys(
                [
                    *current.repository_refs,
                    *[
                        item.repository_ref
                        for item in history
                        if item.repository_ref is not None
                    ],
                ]
            )
        )
        task_refs = tuple(
            dict.fromkeys(
                [
                    *current.task_refs,
                    *[item.task_ref for item in history if item.task_ref is not None],
                ]
            )
        )
        lifecycle = current.lifecycle
        if lifecycle == ImprovementLifecycle.NEW and recurrence >= 2:
            lifecycle = ImprovementLifecycle.RECURRING
        latest = history[-1]
        updated = Improvement(
            schema_version=current.schema_version,
            improvement_id=current.improvement_id,
            skill_id=current.skill_id,
            root_cause_key=current.root_cause_key,
            summary=current.summary,
            recommendation=current.recommendation,
            expected_benefit=current.expected_benefit,
            lifecycle=lifecycle,
            first_seen=first_seen,
            last_seen=last_seen,
            skill_version_ref=current.skill_version_ref or latest.skill_version_ref,
            confidence=latest.confidence if latest.confidence is not None else current.confidence,
            priority=current.priority,
            recurrence=recurrence,
            repository_refs=repository_refs,
            task_refs=task_refs,
            related_skill_ids=current.related_skill_ids,
            relations=current.relations,
            work_refs=current.work_refs,
            merge_lineage=current.merge_lineage,
            revision=current.revision + 1,
            temporal=current.temporal,
            resolution=current.resolution,
            superseded_by_improvement_id=current.superseded_by_improvement_id,
            aliases=current.aliases,
        )
        conn.execute(
            "UPDATE improvements SET payload = ? WHERE improvement_id = ?",
            (serialize_contract(updated.to_dict()), improvement_id),
        )
        return updated
