import json
from datetime import datetime

from agent_brain.core.redaction import REDACT_PLACEHOLDER, redact_sensitive_json
from agent_brain.evidence import score_quality


def test_serializable_quality_assessment_redacts_token_like_scope() -> None:
    token = "ghp_" + "A" * 30
    assessment = score_quality(scope_id=token, as_of=datetime(2026, 1, 1, 0, 0, 0))
    rendered = redact_sensitive_json(assessment.to_dict())
    assert token not in rendered
    assert REDACT_PLACEHOLDER in rendered
    payload = json.loads(rendered)
    assert payload["limitations"]
