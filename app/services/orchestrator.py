import json

from app.services.llm import LLMService
from app.tools.registry import ToolRegistry


class ChatOrchestrator:
    """Coordinates model selection, safe tool execution, and final response."""

    def __init__(self, llm: LLMService, tools: ToolRegistry) -> None:
        self.llm = llm
        self.tools = tools

    async def run(self, messages: list[dict[str, str]]) -> tuple[str, list[str], list[dict[str, str]]]:
        decision = await self.llm.decide(messages, self.tools.schemas())
        if not decision.tool_calls:
            return decision.content or "Yanıt üretilemedi.", [], []

        follow_up: list[dict] = [*messages, {"role": "assistant", "content": decision.content, "tool_calls": [
            {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.arguments)}} for call in decision.tool_calls
        ]}]
        used: list[str] = []
        sources: list[dict[str, str]] = []
        for call in decision.tool_calls:
            result = self.tools.execute(call.name, call.arguments)
            used.append(call.name)
            for match in result.get("matches", []):
                source = {key: str(match.get(key, "")) for key in ("indexed_file_id", "file_name", "relative_path", "directory_path", "allowed_path_id")}
                if source["file_name"] and source not in sources:
                    sources.append(source)
            follow_up.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
        return await self.llm.finalize(follow_up), used, sources

