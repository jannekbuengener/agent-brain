"""Product-neutral identity and provenance primitives."""

from __future__ import annotations

from dataclasses import dataclass


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class StableIdentity:
    """Opaque identity with an explicit namespace owned by the consumer."""

    namespace: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "namespace", _required_text(self.namespace, "namespace"))
        object.__setattr__(self, "value", _required_text(self.value, "value"))


@dataclass(frozen=True, slots=True)
class ProvenanceStamp:
    """Minimal origin pointer without defining a domain-specific source contract."""

    source: str
    reference: str
    content_hash: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "reference", _required_text(self.reference, "reference"))
        if self.content_hash is not None:
            object.__setattr__(
                self,
                "content_hash",
                _required_text(self.content_hash, "content_hash"),
            )
