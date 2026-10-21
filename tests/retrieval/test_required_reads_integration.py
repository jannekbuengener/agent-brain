"""Required-Reads-Integration-Tests (Slice 7, Task 5).

RED-first: Diese Tests definieren das erwartete Verhalten der
produktneutralen Required-Reads-Auflösung für Retrieval und müssen vor
der Implementierung fehlschlagen.
"""

from __future__ import annotations

from agent_brain.context.required_reads import (
    RequiredReadRule,
    RequiredReadsProfile,
)
from agent_brain.retrieval.required_reads import (
    RetrievalRequiredReadsResult,
    resolve_retrieval_required_reads,
)

EMPTY_PROFILE = RequiredReadsProfile(minimum=())


def test_empty_profile_yields_no_required_reads() -> None:
    result = resolve_retrieval_required_reads(
        profile=EMPTY_PROFILE,
        task_scope="generic refactor",
        operation_mode="read",
    )
    assert isinstance(result, RetrievalRequiredReadsResult)
    assert result.required_reads == ()
    assert result.limitations == ("required_reads_profile_empty",)


def test_single_required_read_is_resolved() -> None:
    profile = RequiredReadsProfile(
        minimum=(
            RequiredReadRule(
                path="AGENTS.md",
                priority="critical",
                reason="repository baseline",
            ),
        ),
    )
    result = resolve_retrieval_required_reads(
        profile=profile,
        task_scope="generic task",
        operation_mode="read",
        available_paths=frozenset({"AGENTS.md"}),
    )
    assert len(result.required_reads) == 1
    assert result.required_reads[0].path == "AGENTS.md"
    assert result.required_reads[0].available is True


def test_multiple_required_reads_are_deterministically_ordered() -> None:
    profile = RequiredReadsProfile(
        minimum=(
            RequiredReadRule(path="README.md", priority="low", reason="readme"),
            RequiredReadRule(path="AGENTS.md", priority="critical", reason="baseline"),
        ),
    )
    result = resolve_retrieval_required_reads(
        profile=profile,
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset({"AGENTS.md", "README.md"}),
    )
    paths = [read.path for read in result.required_reads]
    assert paths == ["AGENTS.md", "README.md"]


def test_input_reordering_produces_identical_output() -> None:
    profile_a = RequiredReadsProfile(
        minimum=(
            RequiredReadRule(path="README.md", priority="low", reason="readme"),
            RequiredReadRule(path="AGENTS.md", priority="critical", reason="baseline"),
        ),
    )
    profile_b = RequiredReadsProfile(
        minimum=(
            RequiredReadRule(path="AGENTS.md", priority="critical", reason="baseline"),
            RequiredReadRule(path="README.md", priority="low", reason="readme"),
        ),
    )
    result_a = resolve_retrieval_required_reads(
        profile=profile_a,
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset({"AGENTS.md", "README.md"}),
    )
    result_b = resolve_retrieval_required_reads(
        profile=profile_b,
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset({"AGENTS.md", "README.md"}),
    )
    assert result_a == result_b


def test_duplicate_paths_are_deduplicated() -> None:
    profile = RequiredReadsProfile(
        minimum=(
            RequiredReadRule(path="README.md", priority="low", reason="low"),
            RequiredReadRule(path="README.md", priority="critical", reason="high"),
        ),
    )
    result = resolve_retrieval_required_reads(
        profile=profile,
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset({"README.md"}),
    )
    assert len(result.required_reads) == 1
    assert result.required_reads[0].priority == "critical"


def test_unresolved_read_never_becomes_positive() -> None:
    profile = RequiredReadsProfile(
        minimum=(
            RequiredReadRule(path="docs/missing.md", priority="critical", reason="missing"),
        ),
    )
    result = resolve_retrieval_required_reads(
        profile=profile,
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset(),
    )
    assert len(result.required_reads) == 1
    assert result.required_reads[0].available is False
    assert result.required_reads[0].warning == "not_available"


def test_malformed_rule_is_rejected() -> None:
    try:
        RequiredReadRule(
            path="",
            priority="critical",
            reason="blank path",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("blank path must be rejected")


def test_no_claire_hardcodes() -> None:
    import agent_brain.retrieval.required_reads as mod

    source = mod.__file__ or ""
    assert "claire" not in source.lower()
    assert "trading" not in source.lower()
    assert "surrealdb" not in source.lower()


def test_no_absolute_host_paths() -> None:
    profile = RequiredReadsProfile(
        minimum=(
            RequiredReadRule(path="/etc/passwd", priority="critical", reason="host path"),
            RequiredReadRule(path="C:/Windows/secret", priority="high", reason="host path"),
        ),
    )
    result = resolve_retrieval_required_reads(
        profile=profile,
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset({"/etc/passwd", "C:/Windows/secret"}),
    )
    for read in result.required_reads:
        assert read.available is False
        assert read.warning == "unsafe_path"


def test_repeated_input_identical_output() -> None:
    profile = RequiredReadsProfile(
        minimum=(
            RequiredReadRule(path="AGENTS.md", priority="critical", reason="baseline"),
        ),
    )
    first = resolve_retrieval_required_reads(
        profile=profile,
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset({"AGENTS.md"}),
    )
    second = resolve_retrieval_required_reads(
        profile=profile,
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset({"AGENTS.md"}),
    )
    assert first == second
