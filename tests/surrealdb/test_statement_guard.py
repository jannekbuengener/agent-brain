"""Read-only SurrealQL statement guard tests (#10)."""

from __future__ import annotations

import pytest

from agent_brain.surrealdb import WriteDeniedError, classify_readonly_statement


def test_select_is_allowed() -> None:
    result = classify_readonly_statement("SELECT * FROM repo_artifact LIMIT 5")
    assert result.allowed
    assert result.operation == "SELECT"


def test_writes_are_denied() -> None:
    with pytest.raises(WriteDeniedError):
        classify_readonly_statement("CREATE repo_artifact SET x = 1")
    with pytest.raises(WriteDeniedError):
        classify_readonly_statement("DELETE repo_artifact:1")
    with pytest.raises(WriteDeniedError):
        classify_readonly_statement("INFO FOR ROOT")
    with pytest.raises(WriteDeniedError):
        classify_readonly_statement("SELECT 1; DELETE foo")
