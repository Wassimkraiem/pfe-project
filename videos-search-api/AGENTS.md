# Repository Guidelines

## Project Structure & Module Organization
Core API code lives in `sev/`. The Flask app entrypoint is `sev/app.py` (`bviral_app`), with feature modules under `sev/apps/videos/`:
- `dynamo/` for DynamoDB-backed video operations
- `opensearch/videos/` and `opensearch/indexes/` for search/index APIs

Shared configuration is in `conf/` (`conf.py`, `utils.py`). Root-level helpers include `videosearch_sdk.py` (client SDK), `transformer.py`, and integration test scripts (`test_api.py`, `sdktest.py`). Container and runtime files are at the repo root (`Dockerfile`, `docker-compose.local.yml`, `Makefile`).

## Build, Test, and Development Commands
Use Docker-based workflows by default:
- `make up`: build and start all local services (Flask, DynamoDB Local, OpenSearch).
- `make down`: stop and remove local containers.
- `make logs`: follow service logs.
- `make ps`: list running containers.
- `make create-table`: create the DynamoDB table from `.env` settings.
- `make delete-table`: remove the configured DynamoDB table.
- `pytest -q test_api.py`: run API integration tests.

For manual run inside container, Flask uses `FLASK_APP=sev.app:bviral_app` on port `5000`.

## Coding Style & Naming Conventions
Follow existing Python style:
- 4-space indentation, `snake_case` for functions/variables/modules, `PascalCase` for classes.
- Keep Flask route/view/resource files grouped by domain (`views.py`, `services.py`, `schemas.py`, `resources.py`).
- Prefer small service functions and schema validation at API boundaries.

No formatter/linter is currently enforced in-repo; keep changes consistent with surrounding files.

## Testing Guidelines
Testing uses `pytest` with SDK-driven integration tests (`test_api.py`).
- Name new tests `test_*.py` and test functions `test_*`.
- Keep end-to-end tests deterministic by generating unique IDs (see `unique_video_id()` pattern).
- Start the local stack (`make up`) before running tests that call `http://http://localhost:5000`.

## Commit & Pull Request Guidelines
Recent commits use short, imperative messages (e.g., `fix ranges upload`, `add docker prod`). Prefer:
- `verb + scope` summaries under ~72 chars
- one logical change per commit

PRs should include:
- clear description of behavior changes
- linked issue/task ID when available
- API examples (`curl`/JSON) for endpoint changes
- test evidence (commands run and result)

## Security & Configuration Tips
Never commit real secrets. Keep credentials in `.env` only, and ensure required variables in `conf/conf.py` are set before startup.
