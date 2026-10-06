# SmartOps AI

[![CI](https://github.com/muratshimshek/smartops-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/muratshimshek/smartops-ai/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

SmartOps AI is a self-hosted operations assistant for permission-scoped document search, conversational troubleshooting, and approval-controlled file changes. It supports local OpenAI-compatible model servers such as Ollama as well as hosted providers.

![SmartOps AI web interface](docs/assets/smartops-dashboard.png)

## Capabilities

- FastAPI backend and responsive web interface
- OpenAI-compatible model adapter with native tool calling
- Local fallback mode for integration testing without a model provider
- Conversation persistence with bounded model context
- Administrator-managed filesystem allow-list
- Content indexing for PDF, Word, Excel, PowerPoint, and text formats
- Optional permission-aware semantic retrieval and grounded RAG responses
- Filename and path indexing for other file types
- Source citations with verified file links
- Mandatory approval workflow for file creation and replacement
- Backup, integrity check, path containment, and audit logging
- Automated tests that do not contact paid services

## Architecture

```mermaid
flowchart LR
    Browser[Web client] --> API[FastAPI]
    API --> Orchestrator[Chat orchestrator]
    Orchestrator --> LLM[OpenAI-compatible LLM]
    Orchestrator --> Tools[Allow-listed tools]
    Tools --> Keyword[(Keyword index)]
    Tools --> Retriever[Permission-aware retriever]
    Retriever --> Vectors[(Persistent vectors)]
    Keyword --> Files[Approved directories]
    Vectors --> Files
    API --> Approval[Write approval service]
    Approval --> Files
    API --> DB[(SQLite)]
```

The model cannot access the filesystem directly. It can request only tools registered by the application. File tools query indexes built from administrator-approved directories. Every semantic result is revalidated against the current root permission and real source path; the vector store is never treated as an authorization system. A write proposal remains pending until an administrator explicitly approves it.

See [Architecture](docs/ARCHITECTURE.md) and [Security](docs/SECURITY.md) for implementation details.

Project history and contribution guidance are available in [CHANGELOG.md](CHANGELOG.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Requirements

- Python 3.12 or newer
- Windows, Linux, or macOS for the API
- Windows for the optional native directory picker
- An OpenAI-compatible model server for natural-language responses

## Local setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open the application at `http://localhost:8000` and API documentation at `http://localhost:8000/docs`.

Change `ADMIN_TOKEN` in `.env` before using the management panel. Never commit `.env`.

## Model providers

The management panel can test and activate an OpenAI-compatible endpoint. A typical local Ollama configuration is:

```text
Base URL: http://127.0.0.1:11434/v1
Model:    qwen3:8b
API key:  ollama
```

The connection must succeed before the application saves and activates the configuration. Provider credentials are written only to the ignored local `.env` file and are never returned by the API.

## Document access

Administrators register directories with `read` or `read_write` permission. Content extraction is available for `.txt`, `.md`, `.csv`, `.json`, `.log`, `.xml`, `.yaml`, `.yml`, `.pdf`, `.docx`, `.xlsx`, `.xlsm`, `.xls`, and `.pptx`. Other files remain searchable by filename and relative path. Files exceeding `MAX_INDEX_FILE_BYTES` are skipped.

Indexing never executes discovered files. Symbolic-link and traversal checks prevent access outside approved roots.

## Permission-aware RAG

RAG is optional and disabled by default. When enabled, extracted document text is divided into overlapping, structure-aware chunks. The local embedding provider converts chunks into multilingual vectors, which are persisted in the same SQLite database as the document index. `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` is the default because it supports Turkish and English while remaining practical for local use.

At retrieval time SmartOps joins every chunk to its current `AllowedPath`, requires that root to remain enabled, resolves the real file path, verifies containment, and requires the file to still exist. Revoked roots and deleted or moved files therefore remain inaccessible even if stale vectors exist. Retrieved text is passed to the model as untrusted tool data, and answers expose only verified source metadata. Returned distance is a ranking signal, not a confidence percentage.

The current vector implementation is intentionally simple: vectors are JSON arrays in SQLite and semantic search parses and compares every authorized vector in application memory. Query cost therefore grows linearly with the number of chunks (`O(chunks × dimensions)`). This is suitable for local demonstrations and small-to-medium controlled collections, but it is not an approximate-nearest-neighbor index and should not be presented as a large-scale vector search engine.

Install and enable the optional local embedding stack:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,rag]"
# In .env:
# RAG_ENABLED=true
```

The embedding model is downloaded from Hugging Face by `sentence-transformers` when `SentenceTransformer(model_name)` is first constructed during RAG indexing, reindexing, or semantic search. Merely opening the status panel does not construct or download it. Hugging Face normally caches it under `~/.cache/huggingface/hub` (on Windows, beneath the current user's profile); `HF_HOME` or `HF_HUB_CACHE` can override that location. Later runs reuse a complete cached snapshot. For deliberate offline operation after the first successful download, set `HF_HUB_OFFLINE=1`; startup fails rather than using a partial model if the required snapshot is missing or incomplete. Tests use a deterministic fake provider and never download a model or contact the internet.

For Docker, build the optional dependencies and mount the host directory that should be visible as `/documents`:

```powershell
$env:INSTALL_RAG="true"
$env:SMARTOPS_DOCUMENTS_PATH="C:\Company\Documents"
docker compose up --build
```

Then register `/documents` in the management panel. Application-level `read` or `read_write` permission still applies; the container mount alone does not authorize model access.

## Write approval flow

1. A client proposes a relative path and content.
2. The API verifies that the root has `read_write` permission.
3. The request is stored as `pending`; no file changes occur.
4. An administrator reviews and approves or rejects the request.
5. Approval rechecks the allowed root and the target file hash.
6. Replacements receive a timestamped backup before an atomic write.
7. The decision is recorded in the audit log.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Runtime environment |
| `LLM_MODE` | `demo` | `demo` or `live` |
| `LLM_BASE_URL` | OpenAI API endpoint | OpenAI-compatible API base URL |
| `LLM_MODEL` | `gpt-4o-mini` | Provider model identifier |
| `LLM_API_KEY` | empty | Provider credential; use a non-empty local value for Ollama |
| `LLM_TIMEOUT_SECONDS` | `30` | Provider timeout |
| `DATABASE_URL` | `sqlite:///./smartops.db` | SQLAlchemy database URL |
| `ADMIN_TOKEN` | development placeholder | Management API credential |
| `MAX_CONTEXT_MESSAGES` | `12` | Messages sent to the model |
| `MAX_REQUEST_BYTES` | `16384` | Maximum declared request size |
| `MAX_INDEX_FILE_BYTES` | `5242880` | Maximum indexed file size |
| `MAX_SEARCH_RESULTS` | `20` | Maximum document results |
| `RAG_ENABLED` | `false` | Enables semantic retrieval and the RAG tool |
| `RAG_CHUNK_SIZE` | `1200` | Maximum characters per document chunk |
| `RAG_CHUNK_OVERLAP` | `180` | Characters repeated between adjacent chunks |
| `RAG_TOP_K` | `5` | Maximum semantic results |
| `RAG_MAX_DISTANCE` | `0.65` | Maximum cosine distance accepted as relevant |
| `EMBEDDING_PROVIDER` | `local` | Embedding provider implementation |
| `EMBEDDING_MODEL` | multilingual MiniLM | Local sentence-transformers model identifier |

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Tests use an in-memory database and a deterministic model substitute. They do not read the developer's `.env`, local document index, or provider credentials.

With RAG enabled, index an approved root from the management panel, then test retrieval:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/rag/search `
  -ContentType application/json -Body '{"query":"şirket güvenlik politikası"}'
```

## Production boundary

This repository is suitable for local development and controlled demonstrations. Root-level authorization is not a substitute for per-user document ACLs. Before multi-user or internet-facing deployment, add centralized identity, per-user authorization, TLS, rate limiting, encrypted secret storage, database migrations, and a production database. Do not expose Ollama directly to the public internet.

## Roadmap

- Preserve retrieval-time permission revalidation while introducing per-user document authorization.
- Move embedding generation to a bounded background indexing worker for larger collections.
- Evaluate a real vector index or self-hosted vector database only when corpus size and measured latency justify it; the replacement must not become an authorization layer.

## License

This project is available under the [MIT License](LICENSE).

