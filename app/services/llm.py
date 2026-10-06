import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from openai import AsyncOpenAI, APITimeoutError, APIError

from app.core.config import Settings
from app.core.exceptions import LLMServiceError
from app.prompts.system import ANALYSIS_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from app.schemas.analysis import ITIssueAnalysis, IssueCategory, Severity


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMReply:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMService(Protocol):
    async def analyze(self, issue: str) -> ITIssueAnalysis: ...
    async def decide(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMReply: ...
    async def finalize(self, messages: list[dict[str, Any]]) -> str: ...


class DemoLLMService:
    """Deterministic provider used for local integration checks."""

    async def analyze(self, issue: str) -> ITIssueAnalysis:
        return ITIssueAnalysis(
            category=IssueCategory.OTHER,
            summary=issue.strip(),
            severity=Severity.MEDIUM,
            probable_causes=["Demo modu metnin anlamını değerlendirmez; olası nedenler gerçek bir LLM tarafından üretilmelidir"],
            troubleshooting_steps=["Gerçek analiz için OpenAI uyumlu bir sağlayıcı veya yerel LLM bağlayın"],
            recommended_action="Bu çıktı yalnızca API, şema doğrulaması ve arayüz akışını test eder.",
            escalation_required=False,
        )

    async def decide(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMReply:
        latest = next((str(item.get("content", "")) for item in reversed(messages) if item.get("role") == "user"), "")
        command, _, argument = latest.strip().partition(" ")
        if command == "/status" and argument:
            return LLMReply(tool_calls=[ToolCall("demo-1", "check_service_status", {"service_name": argument})])
        if command == "/guide" and argument:
            return LLMReply(tool_calls=[ToolCall("demo-1", "get_troubleshooting_guide", {"category": argument})])
        if command == "/search" and argument:
            return LLMReply(tool_calls=[ToolCall("demo-1", "search_knowledge_base", {"query": argument})])
        if command == "/files" and argument:
            return LLMReply(tool_calls=[ToolCall("demo-1", "search_allowed_files", {"query": argument})])
        return LLMReply(
            content=(
                "Demo modu doğal dili analiz etmez. Gerçek ve bağlama duyarlı cevaplar için "
                "OpenAI uyumlu bir API veya yerel LLM bağlanmalıdır. Araç akışını denemek için "
                "`/status vpn`, `/guide access`, `/search vpn` veya `/files maliyet` komutlarını kullanabilirsiniz."
            )
        )

    async def finalize(self, messages: list[dict[str, Any]]) -> str:
        raw_result = next((item.get("content", "") for item in reversed(messages) if item.get("role") == "tool"), "")
        try:
            result = json.loads(raw_result)
        except (json.JSONDecodeError, TypeError):
            return "Yerel araç sonucu okunamadı. Lütfen sorunu daha ayrıntılı tarif edin."
        if "status" in result:
            service = result.get("service", "servis").upper()
            status = str(result.get("status", "bilinmiyor")).replace("_", " ")
            return f"Yerel demo durum kaydına göre {service} durumu: {status}. {result.get('detail', '')} Bu gerçek zamanlı operatör verisi değildir; istemci hata mesajı ve bağlantı günlükleriyle doğrulayın."
        if result.get("steps"):
            steps = " ".join(f"{index + 1}) {step}" for index, step in enumerate(result["steps"]))
            return f"Yerel çözüm kılavuzuna göre şu sırayla ilerleyin: {steps} Sonucu ve aldığınız hata mesajını yazarsanız bir sonraki kontrolü daraltabilirim."
        if "matches" in result:
            matches = result.get("matches", [])
            if not matches:
                return "İzin verilen ve indekslenmiş dosyalarda bu sorguyla eşleşen bilgi bulunamadı."
            evidence = " ".join(str(item.get("excerpt", "")) for item in matches[:3]).strip()
            source_names = "; ".join(
                f"{item.get('file_name', '')} — {item.get('directory_path', '')}" for item in matches[:3]
            )
            return f"İzin verilen belgelerde bulunan bilgi: {evidence} Kaynak: {source_names}"
        return "Yerel bilgi araması tamamlandı ancak kesin bir eşleşme bulunamadı. Cihaz, hizmet ve hata mesajı hakkında ek bilgi paylaşın."


class OpenAICompatibleLLMService:
    def __init__(self, settings: Settings) -> None:
        self.client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url, timeout=settings.llm_timeout_seconds)
        self.model = settings.llm_model

    async def test_connection(self) -> None:
        try:
            await self.client.models.list()
        except (APITimeoutError, APIError) as exc:
            raise LLMServiceError("Model sunucusuna bağlantı kurulamadı") from exc

    async def analyze(self, issue: str) -> ITIssueAnalysis:
        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[{"role": "system", "content": ANALYSIS_SYSTEM_PROMPT}, {"role": "user", "content": issue}],
                response_format=ITIssueAnalysis,
            )
            parsed = response.choices[0].message.parsed
            if parsed is None:
                raise LLMServiceError("The provider returned no structured analysis")
            return parsed
        except (APITimeoutError, APIError) as exc:
            raise LLMServiceError("The LLM provider is temporarily unavailable") from exc

    async def decide(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMReply:
        payload = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}, *messages]
        try:
            response = await self.client.chat.completions.create(model=self.model, messages=payload, tools=tools, tool_choice="auto")
            message = response.choices[0].message
            calls = [ToolCall(call.id, call.function.name, json.loads(call.function.arguments)) for call in (message.tool_calls or [])]
            return LLMReply(content=message.content, tool_calls=calls)
        except (APITimeoutError, APIError, json.JSONDecodeError) as exc:
            raise LLMServiceError("The LLM provider could not select a tool") from exc

    async def finalize(self, messages: list[dict[str, Any]]) -> str:
        try:
            response = await self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": CHAT_SYSTEM_PROMPT}, *messages])
            return response.choices[0].message.content or "No response was generated."
        except (APITimeoutError, APIError) as exc:
            raise LLMServiceError("The LLM provider could not generate a final response") from exc


def build_llm_service(settings: Settings) -> LLMService:
    if settings.llm_mode == "demo":
        return DemoLLMService()
    return OpenAICompatibleLLMService(settings)

