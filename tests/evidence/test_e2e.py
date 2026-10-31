from agent_brain import evidence as ev


def test_e2e_pipeline_runs():
    summary = ev.build_trust_summary(
        request=ev.TrustRequest(schema_version="trust-request/v1", scope="neutral"),
    )
    assert summary.schema_version == "trust-summary/v1"
