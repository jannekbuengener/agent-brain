from __future__ import annotations

import json
from pathlib import Path

from agent_brain.context.required_reads import (
    RequiredReadRule,
    RequiredReadsProfile,
    resolve_required_reads,
)

FIXTURE = Path("tests/fixtures/context/required_reads_profile.neutral.v1.json")


def _profile() -> RequiredReadsProfile:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return RequiredReadsProfile(
        minimum=tuple(RequiredReadRule.from_dict(item) for item in payload["minimum"]),
        conditional=tuple(RequiredReadRule.from_dict(item) for item in payload["conditional"]),
    )


def test_minimum_reads_are_always_present_and_stably_ordered() -> None:
    reads = resolve_required_reads(
        profile=_profile(),
        task_scope="small refactor",
        operation_mode="read",
        available_paths=frozenset({"AGENTS.md", "README.md"}),
    )
    assert [item.path for item in reads] == ["AGENTS.md", "README.md"]
    assert all(item.available for item in reads)
    assert all(item.reason and item.priority for item in reads)


def test_keyword_and_operation_mode_conditionals_are_injected() -> None:
    reads = resolve_required_reads(
        profile=_profile(),
        task_scope="change contract schema",
        operation_mode="write",
        available_paths=frozenset({"AGENTS.md", "README.md", "docs/contracts.md", "docs/writes.md"}),
    )
    assert [item.path for item in reads] == [
        "AGENTS.md",
        "docs/writes.md",
        "README.md",
        "docs/contracts.md",
    ]


def test_duplicate_paths_keep_highest_priority_and_stable_reason() -> None:
    profile = RequiredReadsProfile(
        minimum=(RequiredReadRule(path="README.md", priority="medium", reason="baseline"),),
        conditional=(
            RequiredReadRule(
                path="README.md",
                priority="critical",
                reason="write-critical",
                operation_modes=("write",),
            ),
        ),
    )
    reads = resolve_required_reads(profile=profile, task_scope="x", operation_mode="write")
    assert len(reads) == 1
    assert reads[0].priority == "critical"
    assert reads[0].reason == "write-critical"


def test_target_fields_participate_in_keyword_matching() -> None:
    reads = resolve_required_reads(
        profile=_profile(),
        task_scope="generic task",
        target_issue="schema cleanup",
        target_paths=("src/contracts.py",),
        target_symbols=("ContractVersion",),
        target_concepts=("compatibility",),
        operation_mode="read",
    )
    assert "docs/contracts.md" in {item.path for item in reads}


def test_unsafe_paths_never_become_available() -> None:
    unsafe = ("/etc/passwd", "../secret.txt", "C:/secret.txt", "\\\\server\\share\\file.txt")
    profile = RequiredReadsProfile(
        minimum=tuple(
            RequiredReadRule(path=path, priority="critical", reason="unsafe fixture") for path in unsafe
        )
    )
    reads = resolve_required_reads(
        profile=profile,
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset(unsafe),
    )
    assert all(not item.available for item in reads)
    assert all(item.warning == "unsafe_path" for item in reads)


def test_availability_is_caller_supplied_and_missing_path_is_evidence() -> None:
    reads = resolve_required_reads(
        profile=_profile(),
        task_scope="x",
        operation_mode="read",
        available_paths=frozenset({"AGENTS.md"}),
    )
    by_path = {item.path: item for item in reads}
    assert by_path["AGENTS.md"].available is True
    assert by_path["README.md"].available is False
    assert by_path["README.md"].warning == "not_available"


def test_profile_has_no_builtin_product_catalog() -> None:
    empty = RequiredReadsProfile(minimum=())
    assert resolve_required_reads(profile=empty, task_scope="contract trading live-go", operation_mode="write") == ()
