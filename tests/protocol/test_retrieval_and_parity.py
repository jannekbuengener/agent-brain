"""Retrieval contract + CLI/protocol parity (#12)."""

from __future__ import annotations

import json

from agent_brain.cli.main import main
from agent_brain.contracts import ArtifactRef, IndexRecord
from agent_brain.protocol import ProtocolGateway, ProtocolRequest, invoke


def _minimal_record() -> dict[str, object]:
    ref = ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id="art-1",
        source_id="source-widgets",
        source_path="docs/a.md",
        source_hash="hash-1",
    )
    record = IndexRecord(
        schema_version="index-record/v1",
        record_id="rec-1",
        record_type="doc",
        source=ref,
        content_hash="content-1",
        attributes={"title": "build widget", "text": "how to build a widget"},
    )
    return record.to_dict()


def test_retrieval_valid_and_empty_records_are_success() -> None:
    payload = {
        "query": {
            "schema_version": "retrieval-query/v1",
            "query_id": "q1",
            "query_text": "widget",
            "source_id": "source-widgets",
        },
        "records": [_minimal_record()],
        "source_priority": ["source-widgets"],
    }
    response = invoke("retrieval", payload)
    assert response.ok is True
    assert response.data is not None
    assert response.data["result"]["query_id"] == "q1"


def test_retrieval_invalid_query() -> None:
    response = invoke("retrieval", {"query": {"query_id": ""}})
    assert response.ok is False
    assert response.error is not None
    assert response.error.code.value == "invalid_input"


def test_cli_protocol_parity_for_capabilities(capsys) -> None:
    protocol = ProtocolGateway().invoke_sync(ProtocolRequest(operation="capabilities"))
    assert main(["capabilities", "--json"]) == 0
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload["ok"] is protocol.ok
    assert cli_payload["agent_brain_version"] == protocol.agent_brain_version
    assert cli_payload["protocol_schema"] == protocol.protocol_schema
    assert cli_payload["data"]["capabilities"] == protocol.to_dict()["data"]["capabilities"]


def test_cli_protocol_parity_for_version(capsys) -> None:
    protocol = invoke("version")
    assert main(["version", "--json"]) == 0
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload["data"] == protocol.to_dict()["data"]
