from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    conversation_id: UUID | None = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    response: str
    tools_used: list[str] = []
    sources: list["ChatSource"] = []


class ChatSource(BaseModel):
    indexed_file_id: str
    file_name: str
    relative_path: str
    directory_path: str
    allowed_path_id: str


class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ConversationResponse(BaseModel):
    conversation_id: UUID
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

