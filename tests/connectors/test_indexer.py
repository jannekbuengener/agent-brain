from __future__ import annotations

from pathlib import Path

from agent_brain.connectors.indexer import build_repository_index, extract_python_records
from agent_brain.connectors.ingestion import IngestionPolicy
from agent_brain.connectors.scanner import ScannedSource
from agent_brain.contracts import ArtifactRef, RepositoryProfile, RepositorySource


def _profile() -> RepositoryProfile:
    return RepositoryProfile(
        schema_version="repository-profile/v1",
        profile_id="profile-widgets",
        source=RepositorySource(
            schema_version="repository-source/v1",
            source_id="source-widgets",
            repository="example/widgets",
            revision="abc123",
        ),
        include_paths=("src/", "docs/", "config/"),
        allowed_file_types=("python", "markdown", "toml", "json"),
    )


def _source(path: str, text: str) -> ScannedSource:
    return ScannedSource(
        ref=ArtifactRef(
            schema_version="artifact-ref/v1",
            artifact_id=f"artifact-{path.replace('/', '-')}",
            source_id="source-widgets",
            source_path=path,
            source_hash="a" * 64,
            revision="abc123",
        ),
        file_type="python",
        sensitivity=None,
        size_bytes=len(text),
        text=text,
    )


def test_python_extraction_covers_symbols_imports_tests_and_syntax_errors() -> None:
    source = _source(
        "src/widget.py",
        "@decorator\nasync def build_widget():\n    return 1\n\nclass Widget:\n    def method(self):\n        return 2\n\nfrom .helpers import helper\n",
    )
    records, edges, findings = extract_python_records(source, local_module_prefixes=("widgets",))

    assert {record.record_type for record in records} >= {
        "code_symbol",
        "import_reference",
    }
    assert any(record.attributes["name"] == "build_widget" for record in records)
    assert any(record.attributes.get("locality") == "local" for record in records)
    assert {edge.edge_type for edge in edges} == {"imports"}
    assert findings == ()

    broken_records, broken_edges, broken_findings = extract_python_records(
        _source("src/broken.py", "def broken(:\n"), local_module_prefixes=()
    )
    assert broken_records == ()
    assert broken_edges == ()
    assert broken_findings[0].status == "limited"


def test_build_repository_index_uses_only_shared_output_contracts(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "src" / "widget.py").write_text(
        "def build_widget():\n    return 1\n", encoding="utf-8"
    )
    (tmp_path / "src" / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    (tmp_path / "docs" / "widget.md").write_text(
        "# Widget\n\nUse `build_widget`.\n", encoding="utf-8"
    )
    (tmp_path / "config" / "settings.toml").write_text(
        "[widget]\nenabled = true\napi_key = 'must-not-appear'\n", encoding="utf-8"
    )

    result = build_repository_index(tmp_path, _profile(), IngestionPolicy())

    assert {artifact.schema_version for artifact in result.artifacts} == {"artifact-ref/v1"}
    assert {record.schema_version for record in result.records} == {"index-record/v1"}
    assert {edge.schema_version for edge in result.edges} == {"graph-edge/v1"}
    assert {record.record_type for record in result.records} >= {
        "repository_file",
        "code_symbol",
        "document_section",
        "document_chunk",
        "config_reference",
    }
    assert any(finding.status == "limited" for finding in result.findings)
    assert "must-not-appear" not in str([record.to_dict() for record in result.records])


def test_absolute_imports_require_explicit_local_prefix() -> None:
    source = _source("src/widget.py", "import widgets.helper\n")
    records, _, _ = extract_python_records(source, local_module_prefixes=())
    assert records[0].attributes["locality"] == "unknown"

    local_records, _, _ = extract_python_records(source, local_module_prefixes=("widgets",))
    assert local_records[0].attributes["locality"] == "local"


def test_index_fingerprint_is_relocation_and_creation_order_independent(tmp_path: Path) -> None:
    first = tmp_path / "first-host-location"
    second = tmp_path / "second-host-location"
    for root, entries in (
        (first, (("src/widget.py", "def build_widget():\n    return 1\n"), ("docs/widget.md", "# Widget\n"))),
        (second, (("docs/widget.md", "# Widget\n"), ("src/widget.py", "def build_widget():\n    return 1\n"))),
    ):
        for relative_path, content in entries:
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    first_result = build_repository_index(first, _profile(), IngestionPolicy())
    second_result = build_repository_index(second, _profile(), IngestionPolicy())

    assert first_result.fingerprint == second_result.fingerprint
