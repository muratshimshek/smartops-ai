import pytest

from app.core.exceptions import ToolExecutionError
from app.tools.registry import build_tool_registry


def test_tool_execution() -> None:
    result = build_tool_registry().execute("check_service_status", {"service_name": "vpn"})
    assert result["status"] == "performans_düşük"


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(ToolExecutionError):
        build_tool_registry().execute("delete_everything", {})

