# Agentic Helper API

FastAPI chatbot with LangChain + OpenAI and pgvector-backed RAG.

## Features
- Per-user chat memory with a single chat endpoint
- RAG ingestion endpoint
- Retrieval with pgvector cosine similarity
- API key auth (`x-api-key`) and user identifier header (`x-user-id`)
- Startup chatbot initialization (`app.state`) for model/prompt control
- RAG router classifier prompt to decide when retrieval is needed
- Interest classifier label (`INTERESTED` / `NOT_INTERESTED` / `UNCLEAR`) in chat response
- Branch-specific response prompts for `INTERESTED` and `NOT_INTERESTED`

## Quick Start
1. Create a PostgreSQL database and enable `pgvector` extension support.
2. Copy env:
   ```bash
   cp .env.example .env
   ```
3. Install dependencies (example):
   ```bash
   pip install -e .[dev]
   ```
4. Run API:
   ```bash
   uvicorn app.main:app --reload --port 8003
   ```

## Run With Docker
1. Copy env and set your OpenAI key:
   ```bash
   cp .env.example .env
   ```
2. Start services:
   ```bash
   docker compose up --build
   ```
3. Verify health:
   ```bash
   curl http://localhost:8003/health
   ```

Notes:
- `docker-compose.yml` runs `pgvector/pgvector:pg16` for Postgres + vector support.
- API container overrides `DATABASE_URL` to use the `db` service hostname.
- Chatbot settings come from `.env`: `OPENAI_CHAT_MODEL`, `OPENAI_CHAT_TEMPERATURE`, `CHATBOT_SYSTEM_PROMPT`.
- Preferred system prompt source is `CHATBOT_SYSTEM_PROMPT_FILE` (defaults to `data/prompts/bviral_system_prompt.txt`). If file is missing, it falls back to `CHATBOT_SYSTEM_PROMPT`.
- Classifier settings come from `.env`: `OPENAI_CLASSIFIER_MODEL`, `OPENAI_CLASSIFIER_TEMPERATURE`, `CHATBOT_RAG_CLASSIFIER_PROMPT`, `CHATBOT_INTEREST_CLASSIFIER_PROMPT`.
- Interest branch prompts come from `.env`: `CHATBOT_INTERESTED_RESPONSE_PROMPT`, `CHATBOT_NOT_INTERESTED_RESPONSE_PROMPT`.

## API
- `POST /api/v1/chat`
- `POST /api/v1/rag/ingest`
- `POST /api/v1/rag/ingest-excel`

## Example Ingestion
```bash
curl -X POST http://localhost:8003/api/v1/rag/ingest \
  -H "content-type: application/json" \
  -H "x-api-key: change-me" \
  -d '{
    "replace_source": true,
    "documents": [
      {"source": "faq", "text": "Your support hours are Monday-Friday."}
    ]
  }'
```

## Example Chat
```bash
curl -X POST http://localhost:8003/api/v1/chat \
  -H "content-type: application/json" \
  -H "x-api-key: change-me" \
  -H "x-user-id: user-123" \
  -d '{"input_message": "What are your support hours?"}'
```

## Example Excel Ingestion
```bash
curl -X POST http://localhost:8003/api/v1/rag/ingest-excel \
  -H "x-api-key: change-me" \
  -F "file=@/path/to/faq.xlsx" \
  -F "source=faq-excel" \
  -F "question_column=question" \
  -F "answer_column=answer" \
  -F "replace_source=true"
```

The Excel file must be `.xlsx` and include header columns (default names: `question`, `answer`).
