import pytest

from app.services.llm import DemoLLMService


@pytest.mark.asyncio
async def test_demo_llm_requires_no_paid_api() -> None:
    result = await DemoLLMService().analyze("The user cannot access a folder")
    assert result.category == "other"
    assert "Demo modu" in result.probable_causes[0]


@pytest.mark.asyncio
async def test_demo_llm_selects_safe_tool() -> None:
    reply = await DemoLLMService().decide([{"role": "user", "content": "/status vpn"}], [])
    assert reply.tool_calls[0].name == "check_service_status"


@pytest.mark.asyncio
async def test_demo_llm_does_not_pretend_to_understand_natural_language() -> None:
    reply = await DemoLLMService().decide([{"role": "user", "content": "Telefonum çekmiyor"}], [])
    assert "doğal dili analiz etmez" in reply.content
    assert not reply.tool_calls

