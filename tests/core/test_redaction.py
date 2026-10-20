import json
import os
from importlib import import_module
from pathlib import Path


def _redaction_module():
    return import_module("agent_brain.core.redaction")


def test_redact_sensitive_text_masks_generic_assignments_urls_and_addresses() -> None:
    redaction = _redaction_module()
    raw = (
        "API_KEY=top-secret token=abc123 "
        "https://user:pass@example.invalid/private 10.1.2.3"
    )

    rendered = redaction.redact_sensitive_text(raw)

    assert "top-secret" not in rendered
    assert "abc123" not in rendered
    assert "user:pass" not in rendered
    assert "10.1.2.3" not in rendered
    assert redaction.REDACT_PLACEHOLDER in rendered


def test_redact_sensitive_mapping_preserves_structure() -> None:
    redaction = _redaction_module()
    payload = {
        "auth_token": "leaked-token",
        "status": "ok",
        "nested": {"private_key": "secret-value"},
    }

    rendered = redaction.redact_sensitive_mapping(payload)

    assert rendered == {
        "auth_token": redaction.REDACT_PLACEHOLDER,
        "status": "ok",
        "nested": {"private_key": redaction.REDACT_PLACEHOLDER},
    }


def test_redact_sensitive_json_is_parseable_and_deterministic() -> None:
    redaction = _redaction_module()
    payload = {"password": "must-not-appear", "message": "failure"}

    rendered = redaction.redact_sensitive_json(payload)

    assert json.loads(rendered)["password"] == redaction.REDACT_PLACEHOLDER
    assert "must-not-appear" not in rendered
    assert rendered == redaction.redact_sensitive_json(payload)


def test_write_restricted_secret_file_roundtrips_without_inline_config(tmp_path: Path) -> None:
    redaction = _redaction_module()
    target = tmp_path / "credential.pass"

    redaction.write_restricted_secret_file(target, "stored-secret")

    assert target.read_text(encoding="utf-8") == "stored-secret\n"
    if os.name != "nt":
        assert target.stat().st_mode & 0o077 == 0
