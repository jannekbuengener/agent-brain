"""SurrealDB-backed ImprovementObservationStore (#64 / #89).

Sits behind the existing ``ImprovementObservationStore`` port. Observation
events remain append-only and idempotent. Surreal types do not leak into
domain contracts. KnowledgeStore/MemoryStore stay untouched and read-only.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any

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
from agent_brain.surrealdb.config import SurrealDbReadSettings
from agent_brain.surrealdb.http import (
    SurrealHttpProbeResult,
    parse_json_body,
    post_sql,
    probe_version,
)

VersionProber = Callable[..., SurrealHttpProbeResult]
SqlExecutor = Callable[..., SurrealHttpProbeResult]

SCHEMA_VERSION = "improvement-surreal/v1"
IMPROVEMENT_TABLE = "improvement"
OBSERVATION_TABLE = "improvement_observation"

_SCHEMA_STATEMENTS: tuple[str, ...] = (
    f"DEFINE TABLE IF NOT EXISTS {IMPROVEMENT_TABLE} SCHEMALESS;",
    f"DEFINE TABLE IF NOT EXISTS {OBSERVATION_TABLE} SCHEMALESS;",
    f"DEFINE FIELD IF NOT EXISTS improvement_id ON {IMPROVEMENT_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS root_cause_key ON {IMPROVEMENT_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS skill_id ON {IMPROVEMENT_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS lifecycle ON {IMPROVEMENT_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS revision ON {IMPROVEMENT_TABLE} TYPE int;",
    f"DEFINE FIELD IF NOT EXISTS schema_marker ON {IMPROVEMENT_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS payload ON {IMPROVEMENT_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS observation_id ON {OBSERVATION_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS improvement_id ON {OBSERVATION_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS idempotency_key ON {OBSERVATION_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS source_fingerprint ON {OBSERVATION_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS schema_marker ON {OBSERVATION_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS payload ON {OBSERVATION_TABLE} TYPE string;",
    (
        f"DEFINE INDEX IF NOT EXISTS improvement_id_unique ON {IMPROVEMENT_TABLE} "
        "FIELDS improvement_id UNIQUE;"
    ),
    (
        f"DEFINE INDEX IF NOT EXISTS observation_id_unique ON {OBSERVATION_TABLE} "
        "FIELDS observation_id UNIQUE;"
    ),
    (
        f"DEFINE INDEX IF NOT EXISTS observation_idempotency_unique ON {OBSERVATION_TABLE} "
        "FIELDS idempotency_key UNIQUE;"
    ),
    (
        f"DEFINE INDEX IF NOT EXISTS observation_by_improvement ON {OBSERVATION_TABLE} "
        "FIELDS improvement_id;"
    ),
)


def _surreal_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f"'{escaped}'"


def _rows_from_sql_payload(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, list):
        return []
    rows: list[Mapping[str, Any]] = []
    for entry in payload:
        if not isinstance(entry, Mapping):
            continue
        status = entry.get("status")
        if status not in (None, "OK"):
            detail = entry.get("result") or entry.get("message") or status
            raise ImprovementStoreUnavailable(f"surreal statement failed: {detail}")
        result = entry.get("result")
        if isinstance(result, list):
            for row in result:
                if isinstance(row, Mapping):
                    rows.append(row)
        elif isinstance(result, Mapping):
            rows.append(result)
    return rows


def _statement_errors(payload: Any) -> list[str]:
    if not isinstance(payload, list):
        return ["surreal response was not a result list"]
    errors: list[str] = []
    for entry in payload:
        if not isinstance(entry, Mapping):
            errors.append("non-object surreal result entry")
            continue
        status = entry.get("status")
        if status not in (None, "OK"):
            detail = entry.get("result") or entry.get("message") or status
            errors.append(str(detail))
    return errors


_UNIQUE_RE = re.compile(r"unique|already exists|index", re.IGNORECASE)


class SurrealImprovementObservationStore:
    """Append-only ImprovementObservationStore adapter for SurrealDB."""

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

    def __init__(
        self,
        settings: SurrealDbReadSettings | None = None,
        *,
        available: bool = True,
        version_prober: VersionProber | None = None,
        sql_executor: SqlExecutor | None = None,
        ensure_schema: bool = True,
        authorization: str | None = None,
    ) -> None:
        self._settings = settings or SurrealDbReadSettings(
            namespace="agent_brain",
            database="improvements",
        )
        self._available = available
        self._version_prober = version_prober or probe_version
        self._sql_executor = sql_executor or post_sql
        self._authorization = authorization
        self._lock = threading.RLock()
        self._schema_ready = False
        if available and ensure_schema:
            self._ensure_schema()

    @property
    def settings(self) -> SurrealDbReadSettings:
        return self._settings

    def mark_unavailable(self) -> None:
        self._available = False

    def mark_available(self) -> None:
        self._available = True
        self._schema_ready = False
        self._ensure_schema()

    def _ensure_available(self) -> None:
        if not self._available:
            raise ImprovementStoreUnavailable("improvement observation store unavailable")

    def _probe_backend(self) -> None:
        probe = self._version_prober(
            self._settings.endpoint,
            timeout_seconds=self._settings.timeout_seconds,
        )
        if not probe.ok or not probe.version_text:
            raise ImprovementStoreUnavailable(
                probe.error or "surreal endpoint unavailable"
            )
        prefix = self._settings.expected_server_version_prefix
        if prefix and not probe.version_text.startswith(prefix):
            raise ImprovementStoreUnavailable(
                f"surreal version mismatch: expected prefix {prefix!r}, "
                f"got {probe.version_text!r}"
            )

    def _execute(self, sql: str, *, allow_unique_conflict: bool = False) -> list[Mapping[str, Any]]:
        result = self._sql_executor(
            self._settings.endpoint,
            sql,
            namespace=self._settings.namespace,
            database=self._settings.database,
            timeout_seconds=self._settings.timeout_seconds,
            authorization=self._authorization,
        )
        if not result.ok:
            raise ImprovementStoreUnavailable(
                result.error or f"surreal http failure status={result.status_code}"
            )
        payload = parse_json_body(result.body_text)
        errors = _statement_errors(payload)
        if errors:
            joined = "; ".join(errors)
            if allow_unique_conflict and _UNIQUE_RE.search(joined):
                return []
            raise ImprovementStoreUnavailable(f"surreal statement failed: {joined}")
        return _rows_from_sql_payload(payload)

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        self._probe_backend()
        # Ensure NS/DB exist on empty scratch runtimes (separate statements:
        # DEFINE DATABASE requires the namespace header and an empty DB header).
        ns_define = self._sql_executor(
            self._settings.endpoint,
            f"DEFINE NAMESPACE IF NOT EXISTS {self._settings.namespace};",
            namespace="",
            database="",
            timeout_seconds=self._settings.timeout_seconds,
            authorization=self._authorization,
        )
        if not ns_define.ok:
            raise ImprovementStoreUnavailable(
                ns_define.error or "failed to define surreal namespace"
            )
        db_define = self._sql_executor(
            self._settings.endpoint,
            f"DEFINE DATABASE IF NOT EXISTS {self._settings.database};",
            namespace=self._settings.namespace,
            database="",
            timeout_seconds=self._settings.timeout_seconds,
            authorization=self._authorization,
        )
        if not db_define.ok:
            raise ImprovementStoreUnavailable(
                db_define.error or "failed to define surreal database"
            )
        for statement in _SCHEMA_STATEMENTS:
            self._execute(statement)
        # Touch table to prove schema is queryable; empty result is fine.
        self._execute(f"SELECT improvement_id FROM {IMPROVEMENT_TABLE} LIMIT 1;")
        self._schema_ready = True

    def submit_observation(self, observation: ImprovementObservation) -> SubmitObservationResult:
        if not isinstance(observation, ImprovementObservation):
            raise TypeError("observation must be an ImprovementObservation")
        self._ensure_available()
        with self._lock:
            self._ensure_schema()
            existing = self._load_observation_by_idempotency(observation.idempotency_key)
            if existing is not None:
                stored_obs, improvement_id = existing
                improvement = self._load_improvement(improvement_id)
                return SubmitObservationResult(
                    observation=stored_obs,
                    improvement=improvement,
                    created_new_observation=False,
                    created_new_improvement=False,
                )

            improvement_id, root_cause_key = self._resolve_identity(observation)
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

            current = self.get_improvement(improvement_id)
            created_new_improvement = current is None
            if created_new_improvement:
                improvement = self._new_improvement_from_observation(
                    bound, improvement_id, root_cause_key
                )
                self._insert_improvement(improvement)
            else:
                assert current is not None
                if current.skill_id != bound.skill_id:
                    raise InvalidImprovementScope(
                        "observation skill_id does not match existing improvement"
                    )
                if self._observation_id_exists(bound.observation_id):
                    raise ImprovementValidationError(
                        f"observation_id already exists: {bound.observation_id}"
                    )

            inserted = self._insert_observation(bound, improvement_id=improvement_id)
            if not inserted:
                # Lost a unique race on idempotency_key — return canonical row.
                raced = self._load_observation_by_idempotency(bound.idempotency_key)
                if raced is None:
                    raise ImprovementStoreUnavailable(
                        "idempotency conflict without recoverable row"
                    )
                stored_obs, existing_improvement_id = raced
                improvement = self._load_improvement(existing_improvement_id)
                return SubmitObservationResult(
                    observation=stored_obs,
                    improvement=improvement,
                    created_new_observation=False,
                    created_new_improvement=False,
                )

            improvement = self._refresh_aggregate(improvement_id)
            return SubmitObservationResult(
                observation=bound,
                improvement=improvement,
                created_new_observation=True,
                created_new_improvement=created_new_improvement,
            )

    def get_improvement(self, improvement_id: str) -> Improvement | None:
        self._ensure_available()
        self._ensure_schema()
        rows = self._execute(
            "SELECT payload FROM "
            f"{IMPROVEMENT_TABLE} WHERE improvement_id = {_surreal_string(improvement_id)} "
            "LIMIT 1;"
        )
        if not rows:
            return None
        return Improvement.from_dict(json.loads(str(rows[0]["payload"])))

    def list_improvements(
        self,
        *,
        skill_id: str | None = None,
        repository_ref: str | None = None,
        lifecycle: ImprovementLifecycle | str | None = None,
    ) -> tuple[Improvement, ...]:
        self._ensure_available()
        self._ensure_schema()
        lifecycle_filter = None if lifecycle is None else ImprovementLifecycle(lifecycle)
        rows = self._execute(f"SELECT payload FROM {IMPROVEMENT_TABLE};")
        items = [Improvement.from_dict(json.loads(str(row["payload"]))) for row in rows]
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
        self._ensure_schema()
        rows = self._execute(
            "SELECT payload FROM "
            f"{OBSERVATION_TABLE} WHERE improvement_id = {_surreal_string(improvement_id)};"
        )
        items = [
            ImprovementObservation.from_dict(json.loads(str(row["payload"]))) for row in rows
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

    def replace_improvement_aggregate(
        self,
        improvement: Improvement,
        *,
        expected_revision: int | None = None,
    ) -> Improvement:
        """Replace aggregate after management mutation; enforces expected_revision."""
        self._ensure_available()
        with self._lock:
            self._ensure_schema()
            current = self.get_improvement(improvement.improvement_id)
            if current is None:
                raise ImprovementValidationError(
                    f"unknown improvement: {improvement.improvement_id}"
                )
            if expected_revision is not None and current.revision != expected_revision:
                raise ImprovementValidationError(
                    f"revision conflict: expected {expected_revision}, got {current.revision}"
                )
            self._upsert_improvement(improvement)
            return improvement

    def transfer_observations(
        self,
        *,
        source_improvement_id: str,
        target_improvement_id: str,
    ) -> None:
        """Move observation events during merge (append-only event bodies preserved)."""
        self._ensure_available()
        with self._lock:
            self._ensure_schema()
            self._execute(
                f"UPDATE {OBSERVATION_TABLE} SET improvement_id = "
                f"{_surreal_string(target_improvement_id)} "
                f"WHERE improvement_id = {_surreal_string(source_improvement_id)};"
            )

    def export_board_snapshot(self) -> dict[str, Any]:
        """Deterministic JSON export of improvements + observations (no secrets)."""
        self._ensure_available()
        self._ensure_schema()
        improvements = [item.to_dict() for item in self.list_improvements()]
        observations: list[dict[str, object]] = []
        for item in improvements:
            improvement_id = str(item["improvement_id"])
            for obs in self.list_observations(improvement_id):
                observations.append(obs.to_dict())
        observations.sort(
            key=lambda row: (
                str(row.get("improvement_id") or ""),
                str(row.get("timestamp") or ""),
                str(row.get("observation_id") or ""),
            )
        )
        improvements.sort(key=lambda row: str(row["improvement_id"]))
        return {
            "schema_version": SCHEMA_VERSION,
            "runtime": {
                "endpoint_structural": True,
                "namespace": self._settings.namespace,
                "database": self._settings.database,
                "expected_server_version_prefix": self._settings.expected_server_version_prefix,
            },
            "counts": {
                "improvements": len(improvements),
                "observations": len(observations),
            },
            "improvements": improvements,
            "observations": observations,
        }

    def import_board_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        """Import into an empty store; refuses non-empty destination."""
        self._ensure_available()
        with self._lock:
            self._ensure_schema()
            if self.list_improvements() or self._count_observations():
                raise ImprovementValidationError(
                    "refusing import into non-empty surreal improvement store"
                )
            observations = snapshot.get("observations")
            improvements = snapshot.get("improvements")
            if not isinstance(observations, list) or not isinstance(improvements, list):
                raise ImprovementValidationError("invalid improvement board snapshot")
            # Insert improvements first so identity resolution by improvement_id works.
            for raw in improvements:
                if not isinstance(raw, Mapping):
                    raise ImprovementValidationError("invalid improvement row in snapshot")
                improvement = Improvement.from_dict(raw)
                self._insert_improvement(improvement)
            for raw in observations:
                if not isinstance(raw, Mapping):
                    raise ImprovementValidationError("invalid observation row in snapshot")
                observation = ImprovementObservation.from_dict(raw)
                improvement_id = observation.improvement_id
                if improvement_id is None:
                    raise ImprovementValidationError(
                        "snapshot observation missing improvement_id"
                    )
                self._insert_observation(observation, improvement_id=improvement_id)

    def _count_observations(self) -> int:
        rows = self._execute(f"SELECT count() AS count FROM {OBSERVATION_TABLE} GROUP ALL;")
        if not rows:
            return 0
        value = rows[0].get("count", 0)
        return int(value) if value is not None else 0

    def _load_improvement(self, improvement_id: str) -> Improvement:
        improvement = self.get_improvement(improvement_id)
        if improvement is None:
            raise ImprovementValidationError(f"missing improvement aggregate: {improvement_id}")
        return improvement

    def _load_observation_by_idempotency(
        self, idempotency_key: str
    ) -> tuple[ImprovementObservation, str] | None:
        rows = self._execute(
            "SELECT payload, improvement_id FROM "
            f"{OBSERVATION_TABLE} WHERE idempotency_key = {_surreal_string(idempotency_key)} "
            "LIMIT 1;"
        )
        if not rows:
            return None
        payload = ImprovementObservation.from_dict(json.loads(str(rows[0]["payload"])))
        return payload, str(rows[0]["improvement_id"])

    def _observation_id_exists(self, observation_id: str) -> bool:
        rows = self._execute(
            "SELECT observation_id FROM "
            f"{OBSERVATION_TABLE} WHERE observation_id = {_surreal_string(observation_id)} "
            "LIMIT 1;"
        )
        return bool(rows)

    def _insert_improvement(self, improvement: Improvement) -> None:
        payload = serialize_contract(improvement.to_dict())
        sql = (
            f"CREATE {IMPROVEMENT_TABLE} SET "
            f"improvement_id = {_surreal_string(improvement.improvement_id)}, "
            f"root_cause_key = {_surreal_string(improvement.root_cause_key)}, "
            f"skill_id = {_surreal_string(improvement.skill_id)}, "
            f"lifecycle = {_surreal_string(improvement.lifecycle.value)}, "
            f"revision = {int(improvement.revision)}, "
            f"schema_marker = {_surreal_string(SCHEMA_VERSION)}, "
            f"payload = {_surreal_string(payload)};"
        )
        self._execute(sql)

    def _upsert_improvement(self, improvement: Improvement) -> None:
        payload = serialize_contract(improvement.to_dict())
        sql = (
            f"UPDATE {IMPROVEMENT_TABLE} SET "
            f"root_cause_key = {_surreal_string(improvement.root_cause_key)}, "
            f"skill_id = {_surreal_string(improvement.skill_id)}, "
            f"lifecycle = {_surreal_string(improvement.lifecycle.value)}, "
            f"revision = {int(improvement.revision)}, "
            f"schema_marker = {_surreal_string(SCHEMA_VERSION)}, "
            f"payload = {_surreal_string(payload)} "
            f"WHERE improvement_id = {_surreal_string(improvement.improvement_id)};"
        )
        self._execute(sql)

    def _insert_observation(
        self,
        observation: ImprovementObservation,
        *,
        improvement_id: str,
    ) -> bool:
        """Insert observation. Returns True when this call created the row."""
        payload = serialize_contract(observation.to_dict())
        # source_fingerprint mirrors idempotency_key for durable identity evidence.
        fingerprint = observation.idempotency_key
        sql = (
            f"CREATE {OBSERVATION_TABLE} SET "
            f"observation_id = {_surreal_string(observation.observation_id)}, "
            f"improvement_id = {_surreal_string(improvement_id)}, "
            f"idempotency_key = {_surreal_string(observation.idempotency_key)}, "
            f"source_fingerprint = {_surreal_string(fingerprint)}, "
            f"schema_marker = {_surreal_string(SCHEMA_VERSION)}, "
            f"payload = {_surreal_string(payload)};"
        )
        rows = self._execute(sql, allow_unique_conflict=True)
        if rows:
            return True
        existing = self._load_observation_by_idempotency(observation.idempotency_key)
        if existing is not None:
            return False
        raise ImprovementStoreUnavailable(
            "observation insert failed without recoverable idempotency row"
        )

    def _resolve_identity(
        self,
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
        existing = self.get_improvement(observation.improvement_id)
        if existing is None:
            raise ImprovementIdentityAmbiguous(
                "improvement_id unknown and root_cause_key missing; refusing to invent identity"
            )
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

    def _refresh_aggregate(self, improvement_id: str) -> Improvement:
        current = self._load_improvement(improvement_id)
        history = list(self.list_observations(improvement_id))
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
        self._upsert_improvement(updated)
        return updated


def surreal_improvement_indexes() -> Sequence[str]:
    """Documented index names for evidence / ops receipts."""
    return (
        "improvement_id_unique",
        "observation_id_unique",
        "observation_idempotency_unique",
        "observation_by_improvement",
    )
