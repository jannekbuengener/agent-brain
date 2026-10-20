"""Static, dependency-free extraction into the shared index and graph contracts."""

from __future__ import annotations

import ast
import json
import re
import tomllib
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from agent_brain.connectors.ingestion import (
    INGESTION_RESULT_SCHEMA,
    IngestionFinding,
    IngestionPolicy,
    RepositoryIngestionResult,
    build_ingestion_fingerprint,
)
from agent_brain.connectors.scanner import ScannedSource, ScanResult, scan_repository
from agent_brain.contracts import ArtifactRef, GraphEdge, IndexRecord, RepositoryProfile
from agent_brain.core.canonical import canonical_hash
from agent_brain.core.redaction import redact_sensitive_value

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_BACKTICK_RE = re.compile(r"`([A-Za-z_]\w*(?:\.\w+)*)`")


def _record_id(record_type: str, source: ArtifactRef, attributes: Mapping[str, object]) -> str:
    return f"record-{canonical_hash({'type': record_type, 'artifact': source.artifact_id, 'attributes': dict(attributes)})}"


def _record(
    record_type: str,
    source: ArtifactRef,
    attributes: Mapping[str, object],
    *,
    content_hash: str | None = None,
) -> IndexRecord:
    return IndexRecord(
        schema_version="index-record/v1",
        record_id=_record_id(record_type, source, attributes),
        record_type=record_type,
        source=source,
        content_hash=content_hash,
        attributes=attributes,
    )


def _edge(
    edge_type: str,
    from_id: str,
    to_id: str,
    source: ArtifactRef,
    *,
    inferred: bool = False,
) -> GraphEdge:
    return GraphEdge(
        schema_version="graph-edge/v1",
        edge_id=f"edge-{canonical_hash({'type': edge_type, 'from': from_id, 'to': to_id, 'artifact': source.artifact_id})}",
        from_id=from_id,
        to_id=to_id,
        edge_type=edge_type,
        source=source,
        inferred=inferred,
    )


def _qualified_symbols(tree: ast.AST) -> list[tuple[ast.AST, str, str]]:
    symbols: list[tuple[ast.AST, str, str]] = []

    def visit(node: ast.AST, parents: tuple[str, ...] = ()) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                name = ".".join((*parents, child.name))
                symbols.append((child, name, "class"))
                visit(child, (*parents, child.name))
            elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                name = ".".join((*parents, child.name))
                symbols.append((child, name, "async_function" if isinstance(child, ast.AsyncFunctionDef) else "function"))
                visit(child, (*parents, child.name))
            else:
                visit(child, parents)

    visit(tree)
    return symbols


def extract_python_records(
    source: ScannedSource,
    *,
    local_module_prefixes: tuple[str, ...],
) -> tuple[tuple[IndexRecord, ...], tuple[GraphEdge, ...], tuple[IngestionFinding, ...]]:
    """Extract portable Python symbols and imports without importing target code."""
    if source.file_type != "python":
        return (), (), ()
    try:
        tree = ast.parse(source.text, filename=source.ref.source_path)
    except SyntaxError:
        return (), (), (IngestionFinding(source.ref.source_path, "limited", "python syntax error"),)

    records: list[IndexRecord] = []
    edges: list[GraphEdge] = []
    symbols: dict[str, IndexRecord] = {}
    for node, name, symbol_kind in _qualified_symbols(tree):
        decorators = tuple(ast.unparse(value) for value in getattr(node, "decorator_list", ()))
        record = _record(
            "code_symbol",
            source.ref,
            {
                "name": name,
                "symbol_kind": symbol_kind,
                "line": getattr(node, "lineno", 0),
                "decorators": decorators,
            },
        )
        records.append(record)
        symbols[name] = record
        if name.split(".")[-1].startswith("test_"):
            test_record = _record(
                "test_case",
                source.ref,
                {"name": name, "line": getattr(node, "lineno", 0)},
            )
            records.append(test_record)
            edges.append(_edge("tests", test_record.record_id, record.record_id, source.ref))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                locality = "local" if module.split(".", 1)[0] in local_module_prefixes else "unknown"
                record = _record(
                    "import_reference",
                    source.ref,
                    {"module": module, "level": 0, "locality": locality, "line": node.lineno},
                )
                records.append(record)
                edges.append(_edge("imports", record.record_id, f"module:{module}", source.ref, inferred=True))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            locality = "local" if node.level > 0 or module.split(".", 1)[0] in local_module_prefixes else "unknown"
            record = _record(
                "import_reference",
                source.ref,
                {"module": module, "level": node.level, "locality": locality, "line": node.lineno},
            )
            records.append(record)
            edges.append(_edge("imports", record.record_id, f"module:{module}", source.ref, inferred=True))
    return (
        tuple(sorted(records, key=lambda item: item.record_id)),
        tuple(sorted(edges, key=lambda item: item.edge_id)),
        (),
    )


def extract_markdown_records(source: ScannedSource) -> tuple[tuple[IndexRecord, ...], tuple[GraphEdge, ...]]:
    """Extract headings, bounded chunks, and code references from Markdown."""
    if source.file_type != "markdown":
        return (), ()
    records: list[IndexRecord] = []
    edges: list[GraphEdge] = []
    lines = source.text.splitlines()
    sections: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines, start=1):
        match = _HEADING_RE.match(line)
        if match:
            sections.append((index, len(match.group(1)), match.group(2)))
    if not sections:
        sections.append((1, 0, PurePosixPath(source.ref.source_path).stem))
    for position, (line_number, level, title) in enumerate(sections):
        end_line = sections[position + 1][0] - 1 if position + 1 < len(sections) else len(lines)
        section = _record(
            "document_section",
            source.ref,
            {"title": title, "level": level, "line": line_number, "end_line": end_line},
        )
        records.append(section)
        section_text = "\n".join(lines[line_number - 1 : end_line])
        for chunk_index, offset in enumerate(range(0, len(section_text) or 1, 4000)):
            chunk = section_text[offset : offset + 4000]
            chunk_record = _record(
                "document_chunk",
                source.ref,
                {"section": section.record_id, "chunk_index": chunk_index},
                content_hash=canonical_hash({"text": chunk}),
            )
            records.append(chunk_record)
            edges.append(_edge("contains", section.record_id, chunk_record.record_id, source.ref))
        for symbol in sorted(set(_BACKTICK_RE.findall(section_text))):
            reference = _record(
                "doc_code_reference",
                source.ref,
                {"name": symbol, "section": section.record_id},
            )
            records.append(reference)
    return (
        tuple(sorted(records, key=lambda item: item.record_id)),
        tuple(sorted(edges, key=lambda item: item.edge_id)),
    )


def _flatten_config(value: object, prefix: str = "") -> list[tuple[str, object]]:
    if isinstance(value, Mapping):
        flattened: list[tuple[str, object]] = []
        for key in sorted(value, key=str):
            key_text = str(key)
            flattened.extend(_flatten_config(value[key], f"{prefix}.{key_text}" if prefix else key_text))
        return flattened
    return [(prefix, value)]


def extract_config_records(source: ScannedSource) -> tuple[IndexRecord, ...]:
    """Extract TOML/JSON scalar configuration references with sensitive values masked."""
    if source.file_type == "toml":
        try:
            payload: object = tomllib.loads(source.text)
        except tomllib.TOMLDecodeError:
            return ()
    elif source.file_type == "json":
        try:
            payload = json.loads(source.text)
        except json.JSONDecodeError:
            return ()
    else:
        return ()
    return tuple(
        sorted(
            (
                _record(
                    "config_reference",
                    source.ref,
                    {
                        "key": key,
                        "value": redact_sensitive_value(key.split(".")[-1], value),
                    },
                )
                for key, value in _flatten_config(payload)
                if key
            ),
            key=lambda item: item.record_id,
        )
    )


def _file_record(source: ScannedSource) -> IndexRecord:
    return _record(
        "repository_file",
        source.ref,
        {"path": source.ref.source_path, "file_type": source.file_type, "sensitivity": source.sensitivity},
        content_hash=source.ref.source_hash,
    )


def build_repository_index(
    root: Path, profile: RepositoryProfile, policy: IngestionPolicy
) -> RepositoryIngestionResult:
    """Scan a local repository and return deterministic #15 contract outputs."""
    scanned: ScanResult = scan_repository(root, profile, policy)
    records: list[IndexRecord] = []
    edges: list[GraphEdge] = []
    findings = list(scanned.findings)
    for source in scanned.sources:
        file_record = _file_record(source)
        records.append(file_record)
        if source.file_type == "python":
            children, child_edges, child_findings = extract_python_records(
                source, local_module_prefixes=policy.local_module_prefixes
            )
            findings.extend(child_findings)
        elif source.file_type == "markdown":
            children, child_edges = extract_markdown_records(source)
        elif source.file_type in {"toml", "json"}:
            children, child_edges = extract_config_records(source), ()
        else:
            children, child_edges = (), ()
        records.extend(children)
        edges.extend(child_edges)
        edges.extend(_edge("contains", file_record.record_id, child.record_id, source.ref) for child in children)

    symbols = {
        str(record.attributes["name"]): record
        for record in records
        if record.record_type == "code_symbol" and "name" in record.attributes
    }
    for record in records:
        if record.record_type != "doc_code_reference":
            continue
        target = symbols.get(str(record.attributes.get("name", "")))
        if target is not None:
            edges.append(_edge("references", record.record_id, target.record_id, record.source))
    ordered_artifacts = tuple(sorted((source.ref for source in scanned.sources), key=lambda item: item.artifact_id))
    ordered_records = tuple(sorted(records, key=lambda item: item.record_id))
    ordered_edges = tuple(sorted(edges, key=lambda item: item.edge_id))
    ordered_findings = tuple(
        sorted(
            findings,
            key=lambda item: (item.source_path, item.status, item.reason, item.sensitivity or ""),
        )
    )
    return RepositoryIngestionResult(
        schema_version=INGESTION_RESULT_SCHEMA,
        source=profile.source,
        profile_id=profile.profile_id,
        artifacts=ordered_artifacts,
        records=ordered_records,
        edges=ordered_edges,
        findings=ordered_findings,
        fingerprint=build_ingestion_fingerprint(
            source=profile.source,
            profile_id=profile.profile_id,
            artifacts=ordered_artifacts,
            records=ordered_records,
            edges=ordered_edges,
            findings=ordered_findings,
        ),
    )
