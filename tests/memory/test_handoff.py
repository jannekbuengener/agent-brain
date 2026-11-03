"""Fast contract and safety tests for the optional SurrealDB handoff journal."""

from __future__ import annotations

import json
import re

import pytest

from agent_brain.memory.handoff import (
    HandoffConflict,
    HandoffUnavailable,
    SurrealHandoffJournal,
)
from agent_brain.surrealdb.http import SurrealHttpProbeResult


def _ok_version(_endpoint: str, *, timeout_seconds: float) -> SurrealHttpProbeResult:
    del timeout_seconds
    return SurrealHttpProbeResult(ok=True, body_text="surrealdb-3.0.4")


class FakeSurreal:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, str]] = {}
        self.statements: list[str] = []
        self.offline = False
        self.schema_present = True

    def __call__(
        self,
        endpoint: str,
        sql: str,
        *,
        namespace: str,
        database: str,
        timeout_seconds: float,
        authorization: str | None = None,
    ) -> SurrealHttpProbeResult:
        del endpoint, namespace, database, timeout_seconds, authorization
        self.statements.append(sql)
        if self.offline:
            return SurrealHttpProbeResult(ok=False, error="network_down")
        result: list[dict[str, str]] = []
        if sql.startswith("INFO FOR DB"):
            return self._response(
                "OK",
                [
                    {
                        "tables": {"agent_handoff": "DEFINE TABLE agent_handoff"}
                        if self.schema_present
                        else {}
                    }
                ],
            )
        if sql.startswith("CREATE agent_handoff CONTENT"):
            raw = {}
            for name, value in re.findall(r'(\w+):\s*("(?:\\.|[^"\\])*")', sql):
                raw[name] = json.loads(value)
            if raw["event_key"] in self.rows:
                return self._response("ERR", [])
            self.rows[raw["event_key"]] = raw
            result = [raw]
        elif sql.startswith("SELECT * FROM agent_handoff"):
            key = re.search(r"event_key = (\"[^\"]*\")", sql)
            repo = re.search(r"repository_ref = (\"[^\"]*\")", sql)
            task = re.search(r"task_ref = (\"[^\"]*\")", sql)
            if key:
                record = self.rows.get(json.loads(key.group(1)))
                result = [record] if record is not None else []
            elif repo:
                result = [
                    row
                    for row in self.rows.values()
                    if row["repository_ref"] == json.loads(repo.group(1))
                    and (task is None or row["task_ref"] == json.loads(task.group(1)))
                ]
                result = sorted(result, key=lambda r: r["created_at"], reverse=True)
        return self._response("OK", result)

    @staticmethod
    def _response(status: str, data: list[dict[str, str]]) -> SurrealHttpProbeResult:
        return SurrealHttpProbeResult(
            ok=True,
            status_code=200,
            body_text=json.dumps([{"status": status, "result": data}]),
        )


def _input(**overrides: str) -> dict[str, str]:
    data = {
        "repository_ref": "jannekbuengener/agent-brain",
        "agent_id": "claude-code",
        "task_ref": "issue:123",
        "status": "in_progress",
        "summary": "Tests grün, Integration offen",
        "next_step": "Integration abschließen",
        "source_ref": "github:issue:123",
        "idempotency_key": "run-1-end",
    }
    data.update(overrides)
    return data


def _store(fake: FakeSurreal) -> SurrealHandoffJournal:
    return SurrealHandoffJournal(
        authorization="Basic fake",
        sql_executor=fake,
        version_prober=_ok_version,
    )


def test_two_agents_share_handoff_across_journal_instances() -> None:
    fake = FakeSurreal()
    writer = _store(fake)
    first = writer.append(**_input())
    reader = _store(fake)
    records = reader.recall(repository_ref="jannekbuengener/agent-brain", task_ref="issue:123")
    assert records == [first]
    assert records[0].agent_id == "claude-code"
    assert records[0].next_step == "Integration abschließen"
    reader.append(
        **_input(
            agent_id="codex",
            status="completed",
            summary="Integration fertig",
            next_step="Review prüfen",
            idempotency_key="run-2-end",
        )
    )
    assert len(writer.recall(repository_ref="jannekbuengener/agent-brain")) == 2


def test_repo_isolation_and_exact_task_scope() -> None:
    fake = FakeSurreal()
    journal = _store(fake)
    journal.append(**_input())
    journal.append(**_input(repository_ref="jannekbuengener/Claire_de_Binare"))
    assert len(journal.recall(repository_ref="jannekbuengener/agent-brain")) == 1
    assert len(journal.recall(repository_ref="jannekbuengener/Claire_de_Binare")) == 1
    assert journal.recall(repository_ref="jannekbuengener/agent-brain", task_ref="issue:999") == []


def test_idempotent_retry_and_conflicting_content_fail_closed() -> None:
    fake = FakeSurreal()
    journal = _store(fake)
    first = journal.append(**_input())
    assert journal.append(**_input()) == first
    assert len(fake.rows) == 1
    with pytest.raises(HandoffConflict):
        journal.append(**_input(summary="another event with the same key"))
    assert len(fake.rows) == 1


def test_injection_is_a_string_and_not_a_second_statement() -> None:
    fake = FakeSurreal()
    journal = _store(fake)
    journal.append(**_input(summary='"; DELETE agent_handoff; --'))
    sql = next(s for s in fake.statements if s.startswith("CREATE agent_handoff"))
    assert 'summary: "\\"; DELETE agent_handoff; --"' in sql
    assert fake.rows[next(iter(fake.rows))]["summary"] == '"; DELETE agent_handoff; --'


def test_backend_outage_is_error_not_successful_empty() -> None:
    fake = FakeSurreal()
    journal = _store(fake)
    fake.offline = True
    with pytest.raises(HandoffUnavailable):
        journal.recall(repository_ref="jannekbuengener/agent-brain")
    with pytest.raises(HandoffUnavailable):
        journal.append(**_input())


def test_invalid_repository_agent_status_rejected() -> None:
    fake = FakeSurreal()
    journal = _store(fake)
    for item in (
        {"repository_ref": "not-a-repo"},
        {"agent_id": "agent name with spaces"},
        {"status": "execute_code"},
        {"summary": " "},
        {"source_ref": ""},
    ):
        with pytest.raises(ValueError):
            journal.append(**_input(**item))
    with pytest.raises(ValueError):
        journal.recall(repository_ref="repo")
    with pytest.raises(ValueError):
        journal.recall(repository_ref="jannekbuengener/agent-brain", limit=101)
    assert fake.rows == {}


def test_wrong_surreal_major_does_not_initialize_schema() -> None:
    fake = FakeSurreal()

    def wrong(_endpoint: str, *, timeout_seconds: float) -> SurrealHttpProbeResult:
        del timeout_seconds
        return SurrealHttpProbeResult(ok=True, body_text="surrealdb-4.0.0")

    with pytest.raises(HandoffUnavailable):
        SurrealHandoffJournal(sql_executor=fake, version_prober=wrong)
    assert fake.statements == []


def test_missing_schema_is_unavailable_not_empty() -> None:
    fake = FakeSurreal()
    journal = _store(fake)
    fake.schema_present = False
    with pytest.raises(HandoffUnavailable, match="schema unavailable"):
        journal.recall(repository_ref="jannekbuengener/agent-brain")
    assert not any(sql.startswith("SELECT * FROM agent_handoff") for sql in fake.statements)


def test_read_only_journal_does_not_define_schema() -> None:
    fake = FakeSurreal()
    journal = SurrealHandoffJournal(
        authorization="Basic fake",
        sql_executor=fake,
        version_prober=_ok_version,
        initialize=False,
    )
    assert journal.recall(repository_ref="jannekbuengener/agent-brain") == []
    assert not any(sql.startswith("DEFINE ") for sql in fake.statements)
