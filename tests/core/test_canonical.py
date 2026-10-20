import json
from importlib import import_module


def _canonical_module():
    return import_module("agent_brain.core.canonical")


def test_canonical_json_matches_pinned_claire_bytes() -> None:
    canonical = _canonical_module()
    payload = {
        "event_type": "DECISION",
        "event_id": "test-1",
        "ts_ms": 1000,
        "payload": {"decision": "ALLOW", "symbol": "BTCUSDT"},
        "schema_version": "envelope.v1",
    }

    assert canonical.canonical_json_dumps(payload) == (
        '{"event_id":"test-1","event_type":"DECISION",'
        '"payload":{"decision":"ALLOW","symbol":"BTCUSDT"},'
        '"schema_version":"envelope.v1","ts_ms":1000}'
    )


def test_canonical_json_omits_dict_none_but_preserves_list_positions() -> None:
    canonical = _canonical_module()

    rendered = canonical.canonical_json_dumps(
        {"drop": None, "items": [1, None, float("inf")], "keep": 2}
    )

    assert rendered == '{"items":[1,null,null],"keep":2}'


def test_canonical_json_rounds_float_and_normalizes_negative_zero() -> None:
    canonical = _canonical_module()

    rendered = canonical.canonical_json_dumps(
        {"rounded": 1.23456789012345, "zero": -0.0, "nan": float("nan")}
    )

    assert json.loads(rendered) == {"rounded": 1.2345678901, "zero": 0.0}
    assert '"zero":0.0' in rendered


def test_canonical_hash_is_key_order_independent() -> None:
    canonical = _canonical_module()

    assert canonical.canonical_hash({"z": 1, "a": 2, "m": 3}) == canonical.canonical_hash(
        {"a": 2, "m": 3, "z": 1}
    )


def test_sha256_hex_keeps_known_digest_contract() -> None:
    canonical = _canonical_module()

    assert canonical.sha256_hex(b"") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
