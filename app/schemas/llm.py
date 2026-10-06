from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


class LLMConnectionRequest(BaseModel):
    base_url: AnyHttpUrl
    model: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:/-]+$")
    api_key: str = Field(default="ollama", min_length=1, max_length=500)

    @field_validator("api_key")
    @classmethod
    def reject_line_breaks(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("API key cannot contain line breaks")
        return value


class LLMConnectionStatus(BaseModel):
    mode: str
    base_url: str
    model: str
    connected: bool | None = None
    message: str | None = None

