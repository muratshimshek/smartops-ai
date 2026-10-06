from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.api.dependencies import get_llm, get_tools, require_admin_token
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.analysis import AnalyzeRequest, ITIssueAnalysis
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, MessageResponse
from app.schemas.files import (
    AllowedPathCreate,
    AllowedPathResponse,
    AuditLogResponse,
    FileSearchRequest,
    FileSearchResult,
    IndexResponse,
    WriteDecision,
    WriteRequestCreate,
    WriteRequestResponse,
    SemanticSearchResult,
    RAGStatusResponse,
    RAGReindexResponse,
)
from app.schemas.llm import LLMConnectionRequest, LLMConnectionStatus
from app.services.conversations import ConversationService
from app.services.files import FileAccessService
from app.services.llm import LLMService, OpenAICompatibleLLMService, build_llm_service
from app.services.orchestrator import ChatOrchestrator
from app.services.runtime_config import apply_llm_settings, persist_llm_settings
from app.tools.registry import ToolDefinition, ToolRegistry, _string_schema
from app.rag.embeddings import build_embedding_provider
from app.rag.service import RAGService
from app.models.files import DocumentChunk

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]
LlmDep = Annotated[LLMService, Depends(get_llm)]
ToolsDep = Annotated[ToolRegistry, Depends(get_tools)]


def _rag_service(request: Request, db: Session, settings: Settings) -> RAGService:
    if not settings.rag_enabled:
        raise HTTPException(status_code=409, detail="RAG devre dışı")
    provider = getattr(request.app.state, "embedding_provider", None)
    if provider is None:
        provider = build_embedding_provider(settings.embedding_model)
        request.app.state.embedding_provider = provider
    return RAGService(db, settings, provider)


@router.get("/health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict:
    return {"status": "ok", "llm_mode": settings.llm_mode}


@router.post("/api/v1/analyze", response_model=ITIssueAnalysis)
async def analyze(payload: AnalyzeRequest, llm: LlmDep) -> ITIssueAnalysis:
    return await llm.analyze(payload.issue)


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request, db: DbDep, llm: LlmDep, tools: ToolsDep, settings: Annotated[Settings, Depends(get_settings)]) -> ChatResponse:
    service = ConversationService(db)
    conversation = service.get(payload.conversation_id) if payload.conversation_id else service.create()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    service.add_message(conversation, "user", payload.message)
    refreshed = service.get(UUID(conversation.id))
    history = [{"role": msg.role, "content": msg.content} for msg in refreshed.messages[-settings.max_context_messages:]]
    file_service = FileAccessService(db, settings)
    request_tools = tools.extended(
        ToolDefinition(
            "search_allowed_files",
            "İzin verilen ve indekslenmiş kurumsal belgelerde içerik arar.",
            _string_schema("query", "Belge içeriğinde aranacak kısa ve ayırt edici ifade"),
            file_service.search_for_assistant,
        )
    )
    if settings.rag_enabled:
        request_tools = request_tools.extended(
            ToolDefinition(
                "semantic_search_documents",
                "İzin verilen kurumsal belgelerde anlam benzerliğine göre arama yapar.",
                _string_schema("query", "Belgelerde aranacak soru veya kavram"),
                _rag_service(request, db, settings).tool_search,
            )
        )
    answer, tools_used, sources = await ChatOrchestrator(llm, request_tools).run(history)
    service.add_message(conversation, "assistant", answer)
    return ChatResponse(conversation_id=UUID(conversation.id), response=answer, tools_used=tools_used, sources=sources)


@router.get("/api/v1/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: UUID, db: DbDep) -> ConversationResponse:
    conversation = ConversationService(db).get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse(conversation_id=UUID(conversation.id), created_at=conversation.created_at, updated_at=conversation.updated_at, messages=[MessageResponse(role=m.role, content=m.content, timestamp=m.timestamp) for m in conversation.messages])


@router.delete("/api/v1/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: UUID, db: DbDep) -> Response:
    service = ConversationService(db)
    conversation = service.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    service.delete(conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/tools")
def list_tools(tools: ToolsDep, settings: Annotated[Settings, Depends(get_settings)]) -> list[dict[str, str]]:
    result = [
        *tools.public_descriptions(),
        {"name": "search_allowed_files", "description": "İzin verilen ve indekslenmiş kurumsal belgelerde içerik arar."},
    ]
    if settings.rag_enabled:
        result.append({"name": "semantic_search_documents", "description": "İzin verilen belgelerde anlamsal arama yapar."})
    return result


@router.get(
    "/api/v1/admin/llm/status",
    response_model=LLMConnectionStatus,
    dependencies=[Depends(require_admin_token)],
)
def llm_status(settings: Annotated[Settings, Depends(get_settings)]) -> LLMConnectionStatus:
    if settings.llm_mode == "demo":
        return LLMConnectionStatus(
            mode="demo",
            base_url="http://127.0.0.1:11434/v1",
            model="qwen3:8b",
            message="Yerel Ollama için önerilen ayarlar",
        )
    return LLMConnectionStatus(mode=settings.llm_mode, base_url=settings.llm_base_url, model=settings.llm_model)


@router.post(
    "/api/v1/admin/llm/test",
    response_model=LLMConnectionStatus,
    dependencies=[Depends(require_admin_token)],
)
async def test_llm_connection(payload: LLMConnectionRequest, settings: Annotated[Settings, Depends(get_settings)]) -> LLMConnectionStatus:
    candidate = settings.model_copy(update={
        "llm_mode": "live",
        "llm_base_url": str(payload.base_url).rstrip("/"),
        "llm_model": payload.model,
        "llm_api_key": payload.api_key,
        "llm_timeout_seconds": min(settings.llm_timeout_seconds, 8),
    })
    await OpenAICompatibleLLMService(candidate).test_connection()
    return LLMConnectionStatus(mode="live", base_url=candidate.llm_base_url, model=candidate.llm_model, connected=True, message="Bağlantı başarılı")


@router.post(
    "/api/v1/admin/llm/configure",
    response_model=LLMConnectionStatus,
    dependencies=[Depends(require_admin_token)],
)
async def configure_llm(payload: LLMConnectionRequest, request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> LLMConnectionStatus:
    base_url = str(payload.base_url).rstrip("/")
    candidate = settings.model_copy(update={"llm_mode": "live", "llm_base_url": base_url, "llm_model": payload.model, "llm_api_key": payload.api_key, "llm_timeout_seconds": min(settings.llm_timeout_seconds, 8)})
    service = OpenAICompatibleLLMService(candidate)
    await service.test_connection()
    persist_llm_settings(base_url, payload.model, payload.api_key)
    apply_llm_settings(settings, base_url, payload.model, payload.api_key)
    request.app.state.llm = build_llm_service(settings)
    return LLMConnectionStatus(mode="live", base_url=base_url, model=payload.model, connected=True, message="Bağlantı doğrulandı ve etkinleştirildi")


@router.get(
    "/api/v1/admin/paths",
    response_model=list[AllowedPathResponse],
    dependencies=[Depends(require_admin_token)],
)
def list_allowed_paths(db: DbDep, settings: Annotated[Settings, Depends(get_settings)]) -> list:
    return FileAccessService(db, settings).list_allowed_paths()


@router.post(
    "/api/v1/admin/select-directory",
    dependencies=[Depends(require_admin_token)],
)
def select_local_directory(request: Request) -> dict[str, str | None]:
    client_host = request.client.host if request.client else ""
    if client_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="Klasör seçici yalnızca yerel bilgisayarda kullanılabilir")
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(parent=root, title="SmartOps için izin verilecek klasörü seçin")
        root.destroy()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Windows klasör seçicisi açılamadı") from exc
    return {"path": selected or None}


@router.post(
    "/api/v1/admin/paths",
    response_model=AllowedPathResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_token)],
)
def add_allowed_path(payload: AllowedPathCreate, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]):
    return FileAccessService(db, settings).add_allowed_path(payload)


@router.post(
    "/api/v1/admin/paths/{allowed_path_id}/index",
    response_model=IndexResponse,
    dependencies=[Depends(require_admin_token)],
)
def index_allowed_path(allowed_path_id: str, request: Request, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]) -> IndexResponse:
    rag = _rag_service(request, db, settings) if settings.rag_enabled else None
    indexed, skipped, errors = FileAccessService(db, settings, rag).index_path(allowed_path_id)
    return IndexResponse(allowed_path_id=allowed_path_id, indexed_files=indexed, skipped_files=skipped, errors=errors)


@router.delete(
    "/api/v1/admin/paths/{allowed_path_id}",
    response_model=AllowedPathResponse,
    dependencies=[Depends(require_admin_token)],
)
def disable_allowed_path(allowed_path_id: str, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]):
    return FileAccessService(db, settings).disable_allowed_path(allowed_path_id)


@router.post("/api/v1/files/search", response_model=list[FileSearchResult])
def search_files(payload: FileSearchRequest, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]) -> list[FileSearchResult]:
    return FileAccessService(db, settings).search(payload.query, payload.allowed_path_id)


@router.post("/api/v1/rag/search", response_model=list[SemanticSearchResult])
def semantic_search(payload: FileSearchRequest, request: Request, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]):
    results = _rag_service(request, db, settings).search(payload.query)
    return [{
        "indexed_file_id": item.indexed_file_id,
        "allowed_path_id": item.allowed_path_id,
        "file_name": item.file_name,
        "relative_path": item.relative_path,
        "content": item.content,
        "location": item.location,
        "distance": item.distance,
    } for item in results]


@router.get(
    "/api/v1/admin/rag/status",
    response_model=RAGStatusResponse,
    dependencies=[Depends(require_admin_token)],
)
def rag_status(db: DbDep, settings: Annotated[Settings, Depends(get_settings)]):
    return {
        "enabled": settings.rag_enabled,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "indexed_documents": db.scalar(select(func.count(func.distinct(DocumentChunk.indexed_file_id)))) or 0,
        "chunks": db.scalar(select(func.count(DocumentChunk.id))) or 0,
    }


@router.post(
    "/api/v1/admin/rag/reindex",
    response_model=RAGReindexResponse,
    dependencies=[Depends(require_admin_token)],
)
def rag_reindex(request: Request, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]):
    documents, chunks = _rag_service(request, db, settings).reindex_all()
    return {"indexed_documents": documents, "new_or_updated_chunks": chunks}


@router.get("/api/v1/files/{indexed_file_id}/content", response_class=FileResponse)
def get_indexed_file(indexed_file_id: str, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]) -> FileResponse:
    path = FileAccessService(db, settings).resolve_indexed_file(indexed_file_id)
    return FileResponse(path=str(path), filename=path.name, content_disposition_type="inline")


@router.get(
    "/api/v1/admin/write-requests",
    response_model=list[WriteRequestResponse],
    dependencies=[Depends(require_admin_token)],
)
def list_write_requests(db: DbDep, settings: Annotated[Settings, Depends(get_settings)]) -> list:
    return FileAccessService(db, settings).list_write_requests()


@router.post("/api/v1/files/write-requests", response_model=WriteRequestResponse, status_code=status.HTTP_202_ACCEPTED)
def create_write_request(payload: WriteRequestCreate, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]):
    return FileAccessService(db, settings).create_write_request(payload)


@router.post(
    "/api/v1/admin/write-requests/{request_id}/approve",
    response_model=WriteRequestResponse,
    dependencies=[Depends(require_admin_token)],
)
def approve_write_request(request_id: UUID, payload: WriteDecision, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]):
    return FileAccessService(db, settings).approve_write(request_id, payload.actor)


@router.post(
    "/api/v1/admin/write-requests/{request_id}/reject",
    response_model=WriteRequestResponse,
    dependencies=[Depends(require_admin_token)],
)
def reject_write_request(request_id: UUID, payload: WriteDecision, db: DbDep, settings: Annotated[Settings, Depends(get_settings)]):
    return FileAccessService(db, settings).reject_write(request_id, payload.actor)


@router.get(
    "/api/v1/admin/audit-logs",
    response_model=list[AuditLogResponse],
    dependencies=[Depends(require_admin_token)],
)
def get_audit_logs(db: DbDep, settings: Annotated[Settings, Depends(get_settings)]) -> list:
    return FileAccessService(db, settings).audit_logs()

