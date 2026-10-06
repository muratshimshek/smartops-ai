from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import ToolExecutionError
from app.tools.operations import check_service_status, get_troubleshooting_guide, search_knowledge_base


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., dict]

    def openai_schema(self) -> dict[str, Any]:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


class ToolRegistry:
    def __init__(self, tools: list[ToolDefinition]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.openai_schema() for tool in self._tools.values()]

    def public_descriptions(self) -> list[dict[str, str]]:
        return [{"name": tool.name, "description": tool.description} for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> dict:
        tool = self._tools.get(name)
        if not tool:
            raise ToolExecutionError(f"Unknown tool: {name}")
        expected = set(tool.parameters.get("required", []))
        if not expected.issubset(arguments):
            raise ToolExecutionError(f"Missing required arguments for {name}")
        properties = tool.parameters.get("properties", {})
        if tool.parameters.get("additionalProperties") is False and set(arguments) - set(properties):
            raise ToolExecutionError(f"Unexpected arguments for {name}")
        for key, value in arguments.items():
            expected_type = properties.get(key, {}).get("type")
            if expected_type == "string" and not isinstance(value, str):
                raise ToolExecutionError(f"Invalid argument type for {name}.{key}")
        try:
            return tool.function(**arguments)
        except TypeError as exc:
            raise ToolExecutionError(f"Invalid arguments for {name}") from exc

    def extended(self, *tools: ToolDefinition) -> "ToolRegistry":
        return ToolRegistry([*self._tools.values(), *tools])


def _string_schema(name: str, description: str) -> dict:
    return {"type": "object", "properties": {name: {"type": "string", "description": description}}, "required": [name], "additionalProperties": False}


def build_tool_registry() -> ToolRegistry:
    return ToolRegistry([
        ToolDefinition("search_knowledge_base", "Search safe local IT support articles.", _string_schema("query", "Search terms"), search_knowledge_base),
        ToolDefinition("check_service_status", "Check mock status for a known service.", _string_schema("service_name", "Service name"), check_service_status),
        ToolDefinition("get_troubleshooting_guide", "Get a local troubleshooting checklist by category.", _string_schema("category", "Issue category"), get_troubleshooting_guide),
    ])
