import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.files import AllowedPath, DocumentChunk, FileAuditLog, IndexedFile
from app.rag.chunker import DocumentChunker
from app.rag.embeddings import EmbeddingProvider


@dataclass(frozen=True)
class RetrievalResult:
    indexed_file_id: str
    allowed_path_id: str
    file_name: str
    relative_path: str
    directory_path: str
    content: str
    location: str | None
    distance: float


class RAGService:
    def __init__(self, db: Session, settings: Settings, embeddings: EmbeddingProvider) -> None:
        self.db = db
        self.settings = settings
        self.embeddings = embeddings
        self.chunker = DocumentChunker(settings.rag_chunk_size, settings.rag_chunk_overlap)

    def index_file(self, record: IndexedFile) -> int:
        content_hash = hashlib.sha256(record.content.encode("utf-8")).hexdigest()
        existing = self.db.execute(
            select(DocumentChunk.source_sha256, DocumentChunk.embedding_model).where(DocumentChunk.indexed_file_id == record.id).limit(1)
        ).first()
        if existing and existing.source_sha256 == content_hash and existing.embedding_model == self.embeddings.model_name:
            return 0
        self.db.execute(delete(DocumentChunk).where(DocumentChunk.indexed_file_id == record.id))
        chunks = self.chunker.split(record.content)
        if not chunks:
            return 0
        vectors = self.embeddings.embed([chunk.content for chunk in chunks])
        for chunk, vector in zip(chunks, vectors, strict=True):
            self.db.add(DocumentChunk(
                indexed_file_id=record.id,
                allowed_path_id=record.allowed_path_id,
                chunk_index=chunk.index,
                content=chunk.content,
                location=chunk.location,
                source_sha256=content_hash,
                embedding=json.dumps(vector, separators=(",", ":")),
                embedding_model=self.embeddings.model_name,
            ))
        return len(chunks)

    def reindex_all(self) -> tuple[int, int]:
        documents = list(self.db.scalars(
            select(IndexedFile).join(AllowedPath).where(IndexedFile.content != "", AllowedPath.enabled.is_(True))
        ))
        changed = sum(self.index_file(document) for document in documents)
        valid_ids = {document.id for document in documents}
        for chunk in self.db.scalars(select(DocumentChunk)):
            if chunk.indexed_file_id not in valid_ids:
                self.db.delete(chunk)
        self.db.commit()
        return len(documents), changed

    def search(self, query: str, limit: int | None = None) -> list[RetrievalResult]:
        top_k = min(limit or self.settings.rag_top_k, self.settings.rag_top_k)
        query_vector = self.embeddings.embed([query])[0]
        rows = self.db.execute(
            select(DocumentChunk, IndexedFile, AllowedPath)
            .join(IndexedFile, IndexedFile.id == DocumentChunk.indexed_file_id)
            .join(AllowedPath, AllowedPath.id == DocumentChunk.allowed_path_id)
            .where(AllowedPath.enabled.is_(True), DocumentChunk.embedding_model == self.embeddings.model_name)
        ).all()
        ranked: list[tuple[float, RetrievalResult]] = []
        for chunk, document, allowed in rows:
            if not self._currently_authorized(allowed, document):
                continue
            vector = json.loads(chunk.embedding)
            distance = 1.0 - self._cosine(query_vector, vector)
            if distance > self.settings.rag_max_distance:
                continue
            ranked.append((distance, RetrievalResult(
                indexed_file_id=str(document.id),
                allowed_path_id=allowed.id,
                file_name=document.file_name,
                relative_path=document.relative_path,
                directory_path=str(Path(document.absolute_path).parent),
                content=chunk.content,
                location=chunk.location,
                distance=round(distance, 6),
            )))
        ranked.sort(key=lambda item: item[0])
        results = [result for _, result in ranked[:top_k]]
        query_fingerprint = hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]
        self.db.add(FileAuditLog(action="semantic_search", actor="application", target_path="authorized-index", detail=f"query={query_fingerprint}, matches={len(results)}"))
        self.db.commit()
        return results

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.settings.rag_enabled,
            "embedding_provider": self.settings.embedding_provider,
            "embedding_model": self.embeddings.model_name,
            "indexed_documents": self.db.scalar(select(func.count(func.distinct(DocumentChunk.indexed_file_id)))) or 0,
            "chunks": self.db.scalar(select(func.count(DocumentChunk.id))) or 0,
        }

    def tool_search(self, query: str) -> dict:
        matches = self.search(query)
        return {
            "query": query,
            "retrieval": "semantic",
            "matches": [{
                "indexed_file_id": item.indexed_file_id,
                "allowed_path_id": item.allowed_path_id,
                "file_name": item.file_name,
                "relative_path": item.relative_path,
                "directory_path": item.directory_path,
                "excerpt": item.content,
                "location": item.location,
                "distance": item.distance,
            } for item in matches],
        }

    @staticmethod
    def _currently_authorized(allowed: AllowedPath, document: IndexedFile) -> bool:
        try:
            root = Path(allowed.root_path).resolve(strict=True)
            source = Path(document.absolute_path).resolve(strict=True)
            if not source.is_file():
                return False
            return os.path.commonpath([os.path.normcase(str(root)), os.path.normcase(str(source))]) == os.path.normcase(str(root))
        except (OSError, ValueError):
            return False

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if len(left) != len(right) or not left:
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        denominator = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
        return numerator / denominator if denominator else 0.0
