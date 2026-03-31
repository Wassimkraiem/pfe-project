# Repository Guidelines

## Project Structure & Module Organization
- `app/` contains the FastAPI backend.
- `app/api/` defines HTTP routes (`chat.py`, `rag.py`) and DI dependencies (`deps.py`).
- `app/services/` contains orchestration and integrations (LLM chains, RAG ingestion/retrieval, embeddings).
- `app/core/` holds app configuration and startup initialization (`config.py`, `chatbot_init.py`).
- `app/models/`, `app/schemas/`, and `app/db/` hold SQLAlchemy models, Pydantic DTOs, and DB wiring.
- `tests/` contains API-level tests.
- `data/prompts/` stores editable system prompts (for example `bviral_system_prompt.txt`).

## Build, Test, and Development Commands
- Install dependencies: `pip install -e .[dev]`
- Run API locally: `uvicorn app.main:app --reload --port 8003`
- Run with Docker (API + pgvector Postgres): `docker compose up --build`
- Stop containers: `docker compose down`
- Run tests: `python -m pytest -q`
- Quick syntax check: `python -m compileall app tests`

## Coding Style & Naming Conventions
- Use Python 3.11+ conventions with 4-space indentation.
- Prefer explicit type hints for service and API method signatures.
- Keep modules focused: routes in `app/api`, business logic in `app/services`.
- Naming: `snake_case` for functions/variables/files, `PascalCase` for classes, uppercase for constants.
- Keep prompts/configuration externalized in `.env` and `data/prompts/` (avoid hardcoding policy text in handlers).

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio`, `fastapi.testclient`.
- Place tests in `tests/` and name files `test_*.py`.
- Favor endpoint behavior tests with dependency overrides for external services.
- Cover at least: auth checks, chat response schema, RAG ingestion, and classifier routing behavior.

## Commit & Pull Request Guidelines
- No reliable Git history is available in this workspace; use clear Conventional Commit style going forward (e.g., `feat: add excel ingest endpoint`, `fix: enforce classifier fallback`).
- Keep commits scoped to one logical change.
- PRs should include:
  - concise summary and motivation,
  - API contract changes (request/response examples),
  - config/env changes,
  - test evidence (`pytest` output or equivalent).

## Security & Configuration Tips
- Never commit real secrets; keep `.env` local.
- Rotate exposed API keys immediately.
- Validate uploaded files and user input before ingestion.


Foundation

  - Treat LLM apps as distributed systems, not prompt scripts.
  - Separate concerns early: API layer, orchestration layer, model layer, tools/integrations, storage, observability.
  - Start with deterministic chains before moving to autonomous agents.

  Do / Don’t

  - Do use typed inputs/outputs everywhere (pydantic schemas, structured outputs).
  - Do keep prompts versioned as files, not hardcoded strings.
  - Do make routing explicit (RAG, DIRECT, TOOL).
  - Do add strict timeouts, retries, and circuit breakers around every external call.
  - Don’t let the model decide business-critical rules without guardrails.
  - Don’t pass entire chat history blindly; summarize and window it.
  - Don’t deploy without evals and traces.

  LangChain Architecture Best Practice

  - Use LCEL pipelines (PromptTemplate | Model | Parser) for core flows.
  - Use with_structured_output(...) for classifiers and policy decisions.
  - Keep one orchestrator that decides:
  - classify intent
  - choose retrieval/tool usage
  - invoke answer chain
  - apply post-processing/validation
  - Persist conversation state server-side, not client-side.
  - Keep agent loops bounded (max_iterations, tool timeout, budget caps).

  Prompting

  - Use 3 prompt layers:
  - system policy prompt (tone, safety, scope)
  - mode prompt (interested/not interested/support/escalation)
  - task prompt (current user intent + context)
  - Enforce output contracts in prompt and parser.
  - Keep placeholders and policy tokens explicit and test them.
  - Version prompts and run regression evals per change.

  Memory

  - Use short-term memory window (N latest turns).
  - Add long-term memory via summarized state, not raw transcript growth.
  - Store memory with metadata (user_id, locale, domain, confidence).
  - Summarize every few turns to control token growth and drift.

  RAG

  - Chunk by semantics, not only fixed size.
  - Store rich metadata (source, doc_type, timestamp, tenant, permissions).
  - Retrieve with filters first, then similarity.
  - Use hybrid retrieval when exact terms matter (semantic + lexical).
  - Add reranking for quality on larger corpora.
  - Always return citations in response payload for debugging and trust.
  - Re-index incrementally and track embedding model version.

  Agents

  - Start with tool-calling chains before “open-ended agents”.
  - Define tool contracts with strict schemas and idempotency.
  - Validate tool inputs server-side before execution.
  - Add execution limits:
  - tool call count
  - max wall time
  - max token budget
  - Require confirmation for destructive or high-cost actions.
  - Log each tool decision with rationale for auditability.

  Reliability and Safety

  - Add policy gates outside the model for hard rules.
  - Add fallback paths:
  - model unavailable -> safe fallback response
  - retrieval empty -> direct answer with explicit uncertainty
  - tool failure -> degrade gracefully
  - Use allowlists for domains/tools where possible.
  - Redact PII in logs and traces.
  - Never trust model output as executable instructions without validation.

  Evaluation

  - Build offline eval sets for:
  - intent classification accuracy
  - RAG relevance/grounding
  - refusal/redirect behavior
  - tone consistency
  - Track online metrics:
  - first-response latency
  - tool success rate
  - retrieval hit rate
  - hallucination proxy signals
  - user satisfaction
  - Run A/B tests for prompt/model changes.

  Scalability

  - Use async I/O end-to-end.
  - Add request queueing/backpressure for spikes.
  - Cache embeddings and repeated retrieval results.
  - Precompute summaries for long threads.
  - Pool DB connections correctly.
  - Add vector index tuning and periodic vacuum/analyze for pgvector/Postgres.
  - Isolate hot paths: classifier model can be cheaper/smaller than answer model.

  Cost Control

  - Use cheap classifier model, stronger answer model only when needed.
  - Route to RAG only when beneficial.
  - Cap prompt/context size aggressively.
  - Deduplicate retrieval chunks before prompting.
  - Add per-user/session token budgets and alerts.

  Deployment and Ops

  - Keep config in env, prompts in versioned files.
  - Add health/readiness probes for API and dependencies.
  - Trace every request with correlation IDs.
  - Keep model, embedding model, and prompt versions in response metadata for debugging.
  - Use feature flags for new branches/agents.
  - Add migration strategy for conversation schema changes.

  Security

  - Authenticate every endpoint.
  - Enforce tenant isolation in retrieval filters.
  - Sanitize tool inputs and file uploads.
  - Protect secrets with vault/secret manager.
  - Rate-limit by user and API key.

  Practical Build Order

  1. Stable chat chain with structured output.
  2. Add RAG with citation payload.
  3. Add intent/routing classifier.
  4. Add one tool with strict schema.
  5. Add agent orchestration with limits.
  6. Add eval harness and dashboards.
  7. Optimize latency/cost.