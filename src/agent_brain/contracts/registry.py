"""Canonical registry for shared Agent Brain contract schema families."""

from __future__ import annotations

from types import MappingProxyType

from agent_brain.contracts.evidence import CLAIM_REF_SCHEMA, EVIDENCE_REF_SCHEMA
from agent_brain.contracts.index import GRAPH_EDGE_SCHEMA, INDEX_RECORD_SCHEMA
from agent_brain.contracts.provenance import PROVENANCE_SCHEMA
from agent_brain.contracts.repository import (
    ARTIFACT_REF_SCHEMA,
    REPOSITORY_PROFILE_SCHEMA,
    REPOSITORY_SOURCE_SCHEMA,
)
from agent_brain.contracts.resolution import RESOLUTION_META_SCHEMA
from agent_brain.contracts.temporal import TEMPORAL_ENVELOPE_SCHEMA

CONTRACT_SCHEMAS = MappingProxyType(
    {
        "repository-source": REPOSITORY_SOURCE_SCHEMA,
        "repository-profile": REPOSITORY_PROFILE_SCHEMA,
        "artifact-ref": ARTIFACT_REF_SCHEMA,
        "index-record": INDEX_RECORD_SCHEMA,
        "graph-edge": GRAPH_EDGE_SCHEMA,
        "evidence-ref": EVIDENCE_REF_SCHEMA,
        "claim-ref": CLAIM_REF_SCHEMA,
        "temporal-envelope": TEMPORAL_ENVELOPE_SCHEMA,
        "provenance": PROVENANCE_SCHEMA,
        "resolution-meta": RESOLUTION_META_SCHEMA,
    }
)

__all__ = ["CONTRACT_SCHEMAS"]
