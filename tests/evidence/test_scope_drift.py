from datetime import datetime

from agent_brain.evidence import detect_scope_drift
from agent_brain.evidence.contract import ScopeDriftPolicy
from agent_brain.evidence.scope_drift import ScopeDriftBundle


def test_scope_drift_path_out_of_scope():
    report = detect_scope_drift(
        bundle=ScopeDriftBundle(observed_paths=("outside/path",)),
        policy=ScopeDriftPolicy(
            schema_version="scope-drift-policy/v1",
            target_paths=("allowed/",),
        ),
        as_of=datetime(2026, 1, 1),
    )
    assert report.findings
