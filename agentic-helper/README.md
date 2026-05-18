# Agentic Helper API

FastAPI chatbot with LangChain + OpenAI, external Qdrant for RAG, deterministic advanced video search, and optional LangSmith tracing/prompt management.

## Features
- Single chat endpoint with `default`, `video_search`, and `auto` routing modes
- Deterministic `VideoSearchService` over the Videos Search API `/api/videos/advanced-search` endpoint
- Optional Redis-backed conversation memory with in-memory fallback
- RAG ingestion endpoints for JSON and Excel sources
- Retrieval with Qdrant cosine similarity
- API key auth (`x-api-key`) and user identifier header (`x-user-id`)
- Hosted Qdrant support through `QDRANT_URL` and `QDRANT_API_KEY`
- Optional LangSmith tracing and prompt loading
- Startup chatbot initialization (`app.state`) for model and prompt control

## Chat Modes
- `default`: BVIRAL RAG chatbot with interest/RAG classifiers.
- `video_search`: structured video-search plan extraction, deterministic normalization, and advanced hybrid search.
- `auto`: unified router chooses `CHAT_RAG`, `VIDEO_SEARCH`, `DIRECT`, `OUT_OF_SCOPE`, or `SUPPORT_HANDOFF`.

Video-search responses can include `videos`, `search_filters`, `search_action`, `search_url`, `total`, `next_offset`, `execution`, and `fallbacks_used`. RAG responses include `sources` and `citations`.

## Quick Start
1. Copy env:
   ```bash
   cp .env.example .env
   ```
2. Set your external Qdrant endpoint:
   ```bash
   QDRANT_URL=https://your-qdrant-endpoint
   QDRANT_API_KEY=...
   ```
3. Install dependencies:
   ```bash
   pip install -e .[dev]
   ```
4. Run the API:
   ```bash
   uvicorn app.main:app --reload --port 8003
   ```

The service creates the configured Qdrant collection automatically if it does not already exist.

## LangSmith
Tracing is enabled by configuration:
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=agentic-helper
```

Prompts can stay in files and `.env`, or be pulled from LangSmith by setting any of these IDs:
- `CHATBOT_SYSTEM_PROMPT_LANGSMITH`
- `CHATBOT_RAG_CLASSIFIER_PROMPT_LANGSMITH`
- `CHATBOT_ROUTER_PROMPT_LANGSMITH`
- `CHATBOT_INTEREST_CLASSIFIER_PROMPT_LANGSMITH`
- `CHATBOT_INTERESTED_RESPONSE_PROMPT_LANGSMITH`
- `CHATBOT_NOT_INTERESTED_RESPONSE_PROMPT_LANGSMITH`
- `CHATBOT_VIDEO_FILTER_EXTRACTOR_PROMPT_LANGSMITH`
- `VIDEO_SEARCH_SYSTEM_PROMPT_LANGSMITH`

When a LangSmith prompt ID is configured, the app tries LangSmith first and falls back to file/env prompt configuration if the pull fails.

## Docker
The local Docker setup starts the API only. Qdrant is expected to be external and provided through `.env`.

```bash
docker compose up --build
```

## Notes
- Chat history uses Redis when `CHAT_HISTORY_REDIS_URL` is set. Otherwise it falls back to per-process memory.
- Normal video search uses deterministic orchestration. LangGraph remains available as a fallback when advanced search is disabled.
- Prompt files under `data/prompts/` still work without LangSmith.

## API
- `POST /api/v1/chat`
- `POST /api/v1/rag/ingest`
- `POST /api/v1/rag/ingest-excel`
