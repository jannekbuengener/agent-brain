"""CLI export-projection command (pilot implementation for agent-brain#61)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    ImprovementObservation,
)
from agent_brain.improvement import cli
from agent_brain.improvement.sqlite import SqliteImprovementObservationStore


def test_cli_export_projection_writes_vault(tmp_path: Path, capsys) -> None:
    db = tmp_path / "improvements.sqlite3"
    vault = tmp_path / "vault"
    store = SqliteImprovementObservationStore(db)
    store.submit_observation(
        ImprovementObservation(
            schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
            observation_id="cli-obs-1",
            agent_id="cli-agent",
            run_id="cli-run",
            skill_id="cursor-meta-epic-executor",
            observation="CLI must export projection",
            recommendation="Add export-projection subcommand",
            evidence=("evidence:cli-obs-1",),
            timestamp=datetime(2026, 10, 31, 18, 0, tzinfo=UTC),
            idempotency_key="cli-idem-1",
            root_cause_key="pilot-cli-projection-export-missing",
            repository_ref="jannekbuengener/agent-brain",
        )
    )

    code = cli.main(
        [
            "export-projection",
            "--db",
            str(db),
            "--vault",
            str(vault),
            "--generated-at",
            "2026-10-31T19:00:00Z",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "source_hash" in out
    assert (vault / "blackboard").is_dir()
    assert list((vault / "blackboard").rglob("*.md"))
