import json
from datetime import datetime
from importlib import import_module


def _run_id_module():
    return import_module("agent_brain.core.run_id")


def test_timestamp_run_id_preserves_pinned_fourteen_digit_shape() -> None:
    run_id = _run_id_module()
    time = import_module("agent_brain.core.time")
    fixed = time.FixedClock(datetime(2026, 10, 20, 12, 34, 56))

    rendered = run_id.timestamp_run_id(fixed)

    assert rendered == "20261020123456"
    assert rendered.isdigit()
    assert len(rendered) == 14
    assert "%" not in rendered


def test_run_id_from_snapshot_preserves_string_conversion_contract(tmp_path) -> None:
    run_id = _run_id_module()
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"run_id": 123456}), encoding="utf-8")

    assert run_id.run_id_from_snapshot(snapshot) == "123456"
