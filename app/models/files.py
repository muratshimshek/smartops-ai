from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.conversation import utc_now


class AllowedPath(Base):
    __tablename__ = "allowed_paths"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    label: Mapped[str] = mapped_column(String(120))
    root_path: Mapped[str] = mapped_column(Text, unique=True)
    permission: Mapped[str] = mapped_column(String(20), default="read")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IndexedFile(Base):
    __tablename__ = "indexed_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    allowed_path_id: Mapped[str] = mapped_column(ForeignKey("allowed_paths.id", ondelete="CASCADE"), index=True)
    absolute_path: Mapped[str] = mapped_column(Text, unique=True)
    relative_path: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(255), index=True)
    extension: Mapped[str] = mapped_column(String(20))
    size_bytes: Mapped[int] = mapped_column(Integer)
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content: Mapped[str] = mapped_column(Text, default="")
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FileWriteRequest(Base):
    __tablename__ = "file_write_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    allowed_path_id: Mapped[str] = mapped_column(ForeignKey("allowed_paths.id", ondelete="CASCADE"), index=True)
    relative_path: Mapped[str] = mapped_column(Text)
    operation: Mapped[str] = mapped_column(String(20))
    proposed_content: Mapped[str] = mapped_column(Text)
    expected_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    requested_by: Mapped[str] = mapped_column(String(120))
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FileAuditLog(Base):
    __tablename__ = "file_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    target_path: Mapped[str] = mapped_column(Text)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
