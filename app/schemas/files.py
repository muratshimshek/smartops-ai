from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PathPermission(StrEnum):
    READ = "read"
    READ_WRITE = "read_write"


class AllowedPathCreate(BaseModel):
    label: str = Field(min_length=2, max_length=120)
    root_path: str = Field(min_length=3, max_length=1000)
    permission: PathPermission = PathPermission.READ


class AllowedPathResponse(BaseModel):
    id: str
    label: str
    root_path: str
    permission: PathPermission
    enabled: bool
    created_at: datetime


class IndexResponse(BaseModel):
    allowed_path_id: str
    indexed_files: int
    skipped_files: int
    errors: list[str]


class FileSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    allowed_path_id: str | None = None


class FileSearchResult(BaseModel):
    indexed_file_id: str
    file_name: str
    relative_path: str
    absolute_path: str
    extension: str
    modified_at: datetime
    excerpt: str


class WriteRequestCreate(BaseModel):
    allowed_path_id: str
    relative_path: str = Field(min_length=1, max_length=1000)
    content: str = Field(max_length=1_000_000)
    requested_by: str = Field(min_length=2, max_length=120)


class WriteDecision(BaseModel):
    actor: str = Field(min_length=2, max_length=120)


class WriteRequestResponse(BaseModel):
    id: str
    allowed_path_id: str
    relative_path: str
    operation: str
    status: str
    requested_by: str
    approved_by: str | None
    created_at: datetime
    decided_at: datetime | None


class AuditLogResponse(BaseModel):
    id: int
    action: str
    actor: str
    target_path: str
    detail: str
    created_at: datetime
