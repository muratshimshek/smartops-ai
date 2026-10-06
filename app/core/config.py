from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    app_name: str = "SmartOps AI"
    app_env: str = "development"
    llm_mode: Literal["demo", "live"] = "demo"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=30, gt=0, le=120)
    database_url: str = "sqlite:///./smartops.db"
    max_request_bytes: int = Field(default=16_384, ge=1024, le=1_048_576)
    max_context_messages: int = Field(default=12, ge=1, le=50)
    admin_token: str = Field(default="change-me-before-network-use", min_length=12)
    max_index_file_bytes: int = Field(default=5_242_880, ge=1024, le=52_428_800)
    max_search_results: int = Field(default=20, ge=1, le=100)
    rag_enabled: bool = False
    rag_chunk_size: int = Field(default=1200, ge=300, le=8000)
    rag_chunk_overlap: int = Field(default=180, ge=0, le=2000)
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_max_distance: float = Field(default=0.65, ge=0, le=2)
    embedding_provider: Literal["local"] = "local"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def require_live_api_key(self) -> "Settings":
        if self.llm_mode == "live" and not self.llm_api_key:
            raise ValueError("LLM_API_KEY is required when LLM_MODE=live")
        if self.app_env != "development" and self.admin_token == "change-me-before-network-use":
            raise ValueError("ADMIN_TOKEN must be changed outside development")
        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

