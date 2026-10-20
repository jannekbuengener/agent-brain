"""Explicit version parsing and compatibility checks for shared contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass

_VERSION_RE = re.compile(r"^(?P<family>[a-z0-9][a-z0-9-]*)/v(?P<major>[1-9][0-9]*)$")


@dataclass(frozen=True, slots=True)
class ContractVersion:
    """Parsed contract family and major version."""

    family: str
    major: int

    @classmethod
    def parse(cls, value: str) -> ContractVersion:
        if not isinstance(value, str):
            raise TypeError("contract version must be a string")
        match = _VERSION_RE.fullmatch(value)
        if match is None:
            raise ValueError(f"invalid contract version: {value!r}")
        return cls(family=match.group("family"), major=int(match.group("major")))

    def __str__(self) -> str:
        return f"{self.family}/v{self.major}"


def require_compatible_version(
    value: str,
    *,
    expected_family: str,
    supported_major: int,
) -> ContractVersion:
    """Return parsed version or reject an incompatible family/major fail-closed."""
    version = ContractVersion.parse(value)
    if version.family != expected_family:
        raise ValueError(
            f"contract family mismatch: expected {expected_family!r}, got {version.family!r}"
        )
    if version.major != supported_major:
        raise ValueError(
            f"contract major mismatch: expected v{supported_major}, got v{version.major}"
        )
    return version
