# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Optional local multilingual embeddings and persistent semantic document retrieval
- Permission-aware RAG tool with grounded source attribution
- RAG status, reindexing, and root-revocation controls in the management panel
- Deterministic offline tests for chunking, persistence, reindexing, and authorization boundaries

### Security

- Retrieval-time root and source-path authorization for every semantic result
- Prompt-injection boundary for untrusted retrieved document content
- Strict tool argument type and additional-property validation
- Non-root Docker runtime, health check, and reduced build context

### Planned

- User authentication and per-document authorization
- OCR for scanned documents and images
- Production database migrations

## [0.1.0] - 2026-10-06

### Added

- FastAPI API and responsive web interface
- OpenAI-compatible model integration with local fallback mode
- Ollama connection testing and runtime activation
- Conversation persistence and bounded context
- Administrator-managed filesystem allow-list
- Content indexing for common office and text formats
- Source-linked document search
- Approval-controlled file creation and replacement
- Backup, integrity verification, containment checks, and audit logs
- Docker configuration and automated test suite
- Architecture, security, and contribution documentation

[Unreleased]: https://github.com/muratshimshek/smartops-ai/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/muratshimshek/smartops-ai/releases/tag/v0.1.0

