import pytest
from pydantic import ValidationError

from app.schemas.analysis import ITIssueAnalysis


def test_structured_output_rejects_invalid_enum() -> None:
    with pytest.raises(ValidationError):
        ITIssueAnalysis(category="made-up", summary="Valid summary", severity="medium", probable_causes=["Cause"], troubleshooting_steps=["Step"], recommended_action="Action", escalation_required=False)

