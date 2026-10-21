"""Internal validation helpers shared by versioned Agent Brain contracts."""

from __future__ import annotations

from datetime import UTC, datetime


def required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return required_text(value, field_name)


def text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise TypeError(f"{field_name} must be a list or tuple of strings")
    return tuple(required_text(item, field_name) for item in values)


def normalize_utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def parse_utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return normalize_utc_datetime(value, field_name)
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a datetime or ISO datetime string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must not be blank")
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO datetime") from exc
    return normalize_utc_datetime(parsed, field_name)


def parse_optional_utc_datetime(value: object, field_name: str) -> datetime | None:
    if value is None:
        return None
    return parse_utc_datetime(value, field_name)


def format_utc_datetime(value: datetime) -> str:
    normalized = normalize_utc_datetime(value, "datetime")
    return f"{normalized.isoformat()}Z"


def optional_unit_interval(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number in [0.0, 1.0]")
    normalized = float(value)
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"{field_name} must be in [0.0, 1.0]")
    return normalized
