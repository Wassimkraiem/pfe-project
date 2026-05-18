# BVIRAL Monorepo — Agent Guide

## Structure

| Directory | Role | Tech | Internal:Host port |
|---|---|---|---|
| `AR-api/` | Auth, billing, onboarding, admin API | FastAPI + PostgreSQL + Celery | `8000:8001` |
| `videos-search-api/` | Video index & search | Flask + OpenSearch 3.x + Redis | `5000:5000` |
| `agentic-helper/` | AI chatbot (RAG + video search agent) | FastAPI + Qdrant + OpenAI | `8003:8003` |
| `authentic_rights_portal/` | Rights/billing frontend | Next.js 16 + MUI 7 | `3001:3001` |
| `videosearchv0/` | Video discovery frontend | Next.js 15 + Tailwind/shadcn | `3000:3002` |

Each service has its own `AGENTS.md` with deeper detail — read those before editing.

## Dev Commands

```bash
# Full stack
docker compose up -d --build         # start everything
docker compose logs -f <service>     # follow one service

# AR-api (cd AR-api)
python -m pytest -q                  # run tests (dir exists, no test files yet)
alembic revision --autogenerate -m "msg"   # new migration
alembic upgrade head                 # apply migrations

# videos-search-api (cd videos-search-api)
make up / make down                  # start/stop its own Docker stack
python -m pytest -q test_search_accuracy_speed.py -s   # search eval benchmark

# agentic-helper (cd agentic-helper)
python -m pytest -q                  # run tests (tests/test_api.py, 11 tests)

# authentic_rights_portal (cd authentic_rights_portal)
npm run dev                          # dev server on :3001
npm run lint && npm run format:check # lint + format

# videosearchv0 (cd videosearchv0)
npm run dev                          # dev server on :3000 (host :3002)
```

## Key Architecture (AR-api)

- **Router prefixes**: `/auth`, `/users`, `/canto`, `/onboarding_sessions`, `/channels`, `/conversations`, `/playlists`, `/recommendations`, `/video-submissions`, `/payments`, plus `/webhook` (no prefix — registered **first** in `app/app.py:58` so Stripe webhooks match before payment routes).
- **Module pattern**: `router.py` → `services.py` → `models.py` + `schemas.py` + `exceptions.py`. Every client error uses `AppError` subclasses with `error_code` — never raw `HTTPException`.
- **Alembic**: `alembic/env.py` must import all model modules; each feature package's `__init__.py` must import its ORM models for autogenerate to see tables.
- **Canto**: Canto DAM user provisioning is **prod-only** (`settings.canto_enabled`). In non-prod, Celery tasks log a skip message and return early.
- **CORS**: `CORS_ORIGINS` is comma-separated exact URLs. `allow_credentials=True` means `*` is not allowed.
- **Async threads**: `ASYNCIO_THREAD_POOL_SIZE=20` (default) handles blocking JWT + Stripe calls via `asyncio.to_thread`.

## Frontend Split

- **authentic_rights_portal** (`:3001`): handles signup, billing, admin. Links to content portal at `NEXT_PUBLIC_CONTENT_PORTAL_URL` (`:3002/dashboard`).
- **videosearchv0** (`:3002`): video library browsing/search/playback. Auth redirects to the rights portal — it is NOT self-contained for auth.
- **API proxies**: Both Next.js apps proxy backend calls through `app/api/` routes (e.g., `/api/chat` → agentic-helper, `/api/videos/query` → videos-search-api).
- **Search personalization**: `videosearchv0` records search and click events to `AR-api /recommendations/events/*` for per-user recommendation profiles and renders a "Recommended for You" section on the home dashboard (before "Browse by Category").

## Agentic-helper Chat Modes

- `"default"` mode: RAG chatbot (classify interest → retrieve from Qdrant → answer with `gpt-4o-mini`).
- `"video_search"` mode: LangGraph ReAct agent with 4 tools (semantic search, filter search, categories, facets). Extracts structured `VideoSearchFilterPlan` via `with_structured_output`.
- Prompts live in `data/prompts/` (3-tier resolution: LangSmith → file → hardcoded fallback).
- All RAG CRUD + transcribe endpoints require `x-api-key` header.

## Testing Notes

- `AR-api/tests/` directory exists but has zero test files.
- `agentic-helper/tests/test_api.py` has working tests (FastAPI TestClient with dependency overrides).
- `videos-search-api/test_api.py` and `test_search_accuracy_speed.py` are integration tests needing the full Docker stack running.
- No test framework exists in either frontend app.

## Gotchas

- `.env` files are gitignored globally. Each service uses its own `.env` + `.env.example`. Copy the example, never commit `.env`.
- `videos-search-api` Docker `working_dir: /sev` (not `/app`). Flask entry: `FLASK_APP=sev.app:bviral_app`.
- No pre-commit hooks, no typecheck config in any service. `videos-search-api` has no enforced linter/formatter.
- The per-service `docker-compose*.yml` files (in `AR-api/`, `videos-search-api/`, `agentic-helper/`) are for running that service in isolation. Root `docker-compose.yml` runs everything together.
- Terraform + ECS deploy infra is in `AR-api/ssm_store/`. CI is Bitbucket Pipelines (not GitHub Actions).
