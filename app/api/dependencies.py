import secrets

from fastapi import Header, HTTPException, Request

from app.services.llm import LLMService
from app.tools.registry import ToolRegistry


def get_llm(request: Request) -> LLMService:
    return request.app.state.llm


def get_tools(request: Request) -> ToolRegistry:
    return request.app.state.tools


def require_admin_token(
    request: Request,
    x_admin_token: str | None = Header(default=None),
) -> None:
    expected = request.app.state.settings.admin_token
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="Geçersiz yönetici anahtarı")

