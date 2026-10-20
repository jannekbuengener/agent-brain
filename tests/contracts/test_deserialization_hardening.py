from __future__ import annotations

import pytest

from agent_brain.contracts.evidence import ClaimRef, EvidenceRef
from agent_brain.contracts.index import GraphEdge, IndexRecord
from agent_brain.contracts.repository import ArtifactRef, RepositoryProfile, RepositorySource
from agent_brain.contracts.versioning import ContractVersion

ARTIFACT = {
    "schema_version": "artifact-ref/v1",
    "artifact_id": "artifact-example",
    "source_id": "source-example",
    "source_path": "src/widget.py",
    "source_hash": "a" * 64,
}

SOURCE = {
    "schema_version": "repository-source/v1",
    "source_id": "source-example",
    "repository": "example/widgets",
}


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (
            lambda: RepositorySource.from_dict({**SOURCE, "source_id": None}),
            "source_id",
        ),
        (
            lambda: RepositoryProfile.from_dict(
                {
                    "schema_version": "repository-profile/v1",
                    "profile_id": 7,
                    "source": SOURCE,
                }
            ),
            "profile_id",
        ),
        (
            lambda: ArtifactRef.from_dict({**ARTIFACT, "artifact_id": None}),
            "artifact_id",
        ),
        (
            lambda: IndexRecord.from_dict(
                {
                    "schema_version": "index-record/v1",
                    "record_id": None,
                    "record_type": "module",
                    "source": ARTIFACT,
                }
            ),
            "record_id",
        ),
        (
            lambda: GraphEdge.from_dict(
                {
                    "schema_version": "graph-edge/v1",
                    "edge_id": "edge-example",
                    "from_id": 7,
                    "to_id": "record-b",
                    "edge_type": "contains",
                }
            ),
            "from_id",
        ),
        (
            lambda: EvidenceRef.from_dict(
                {
                    "schema_version": "evidence-ref/v1",
                    "evidence_id": None,
                    "evidence_type": "observation",
                }
            ),
            "evidence_id",
        ),
        (
            lambda: ClaimRef.from_dict(
                {
                    "schema_version": "claim-ref/v1",
                    "claim_id": 7,
                    "claim_type": "assertion",
                }
            ),
            "claim_id",
        ),
    ],
)
def test_from_dict_rejects_wrong_required_text_types(factory, field: str) -> None:
    with pytest.raises(TypeError, match=field):
        factory()


def test_contract_version_rejects_noncanonical_whitespace() -> None:
    with pytest.raises(ValueError, match="invalid contract version"):
        ContractVersion.parse(" repository-source/v1 ")
