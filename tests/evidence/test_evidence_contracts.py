from dataclasses import FrozenInstanceError
import pytest
from agent_brain.evidence.contract import QualityPolicy, compute_weighted_mean
from tests.evidence.conftest import evidence_state

def test_evidence_state_frozen():
    state = evidence_state()
    with pytest.raises(FrozenInstanceError):
        state.strength = "strong"  # type: ignore[misc]

def test_quality_policy_defaults():
    policy = QualityPolicy.default()
    assert policy.dependency_confidence_threshold == 0.5
    assert policy.grade_bands["blocking"] == 0.30

def test_weighted_mean_relative_weights():
    result = compute_weighted_mean(((1.0, 2.0), (0.0, 1.0), (0.0, 1.0)))
    assert result == pytest.approx(0.5)
