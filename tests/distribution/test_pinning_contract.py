from __future__ import annotations

import pytest

from agent_brain.distribution import (
    DISTRIBUTION_MODEL,
    PinKind,
    PinSpec,
    format_requirement,
    parse_pin_spec,
    reject_moving_ref,
    verify_installed_version,
    version_git_tag,
)
from agent_brain.distribution.version import get_package_version


def test_distribution_model_is_exact_version_plus_matching_tag() -> None:
    assert DISTRIBUTION_MODEL == "exact-package-version+matching-git-tag"


@pytest.mark.parametrize(
    "requirement,kind,version,reference",
    [
        ("agent-brain==0.1.0", PinKind.EXACT_VERSION, "0.1.0", "0.1.0"),
        (
            "agent-brain @ git+https://github.com/jannekbuengener/agent-brain.git@v0.1.0",
            PinKind.GIT_TAG,
            "0.1.0",
            "v0.1.0",
        ),
        (
            "agent-brain @ git+https://github.com/jannekbuengener/agent-brain.git@56f8a0a8408fc6d1c7b346d018999be020b258b9",
            PinKind.GIT_COMMIT,
            None,
            "56f8a0a8408fc6d1c7b346d018999be020b258b9",
        ),
    ],
)
def test_parse_canonical_pins(
    requirement: str,
    kind: PinKind,
    version: str | None,
    reference: str,
) -> None:
    pin = parse_pin_spec(requirement)
    assert pin.kind is kind
    assert pin.version == version
    assert pin.reference == reference


@pytest.mark.parametrize(
    "requirement",
    [
        "agent-brain @ git+https://github.com/jannekbuengener/agent-brain.git@main",
        "agent-brain @ git+https://github.com/jannekbuengener/agent-brain.git@latest",
        "agent-brain @ git+https://github.com/jannekbuengener/agent-brain.git@HEAD",
        "agent-brain @ git+https://github.com/jannekbuengener/agent-brain.git@origin/main",
        "../agent-brain",
        "./src",
        "D:/Dev/Workspaces/Repos/agent-brain",
    ],
)
def test_moving_and_local_pins_are_rejected(requirement: str) -> None:
    with pytest.raises(ValueError):
        parse_pin_spec(requirement)


def test_format_requirement_round_trip() -> None:
    exact = PinSpec(kind=PinKind.EXACT_VERSION, version="0.1.0", reference="0.1.0")
    tag = PinSpec(kind=PinKind.GIT_TAG, version="0.1.0", reference=version_git_tag("0.1.0"))

    assert format_requirement(exact) == "agent-brain==0.1.0"
    assert format_requirement(tag).endswith("@v0.1.0")
    assert parse_pin_spec(format_requirement(exact)) == exact


def test_reject_moving_ref_helper() -> None:
    with pytest.raises(ValueError, match="moving"):
        reject_moving_ref("main")


def test_verify_installed_version_matches_pin() -> None:
    current = get_package_version()
    assert verify_installed_version(current) == current
    with pytest.raises(ValueError, match="does not match"):
        verify_installed_version("9.9.9")
