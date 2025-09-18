# Repository Guidelines

## Project Structure & Module Organization
The project targets a unified Python stack that merges the RSS ingestion, AI orchestration, mailer, and dashboard flows from the legacy Aggregator repos. Keep core application code under `app/` with logical subpackages such as `ingest/`, `ai/`, `email/`, `web/`, and `config/`. Scheduler tasks and CLI utilities live in `app/tasks/`. Front-end templates, static assets, and dashboard UI components belong in `app/web/templates/` and `app/web/static/`. Persisted settings (SQLite) and migrations stay in `data/`, while container assets reside in `docker/`. Place automated tests in `tests/`, mirroring the source tree.

## Build, Test, and Development Commands
Create a virtualenv and install dependencies with `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`. Run the local stack via `uvicorn app.web.main:app --reload` to serve the dashboard and background scheduler. Execute an end-to-end dry run from the CLI with `python -m app.tasks.run_once`. Tests are executed using `pytest`; add `--cov=app` for coverage checks. Build the deployment image with `docker build -t market-aggregator .` and run it locally using `docker run --env-file .env -p 8000:8000 market-aggregator`.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation, descriptive type hints, and snake_case modules. Classes use PascalCase and constants stay UPPER_SNAKE_CASE. Naming for async tasks follows the `verb_noun_task` pattern (e.g., `fetch_feeds_task`). Format code with `ruff check --fix` and `black app tests`. Prefer dependency injection for external services (AI providers, Resend client) to ease testing.

## Testing Guidelines
Use `pytest` for unit and integration tests. Organize test files as `tests/<module>/test_*.py`, grouping fixtures in `tests/conftest.py`. New features require at least one happy-path test and one failure-path or edge-case test. Run `pytest --cov=app --cov-report=term-missing` before opening a pull request. Mock AI and email providers to avoid external calls.

## Commit & Pull Request Guidelines
Write commits in the imperative mood (e.g., “Add Resend retry policy”). Aggregate related changes into focused commits under 200 lines when possible. Pull requests should link issues, summarize behavioral changes, describe testing performed, and include screenshots or curl transcripts for dashboard-visible updates. Request review before merging and ensure CI pipelines (lint, tests, docker build) pass.

## Security & Configuration Tips
Store secrets (API keys, Resend tokens) in `.env` and never commit them. Document required environment variables in `config/settings.py` and provide safe defaults for local development. Rotate keys used in tests and scrub logs before sharing artifacts.

## 2025-09-17 Integration Notes
- Added `app/config/timezones.py`, `app/config/models.py`, and `/api/meta/options` so the dashboard and global settings share the same curated timezone/model catalogs.
- Extended global settings to support editable primary/secondary models, reasoning level, and recipient list; updates now propagate into the AI cascade (`app/config/settings.py`, `app/web/api/schemas.py`, `app/web/api/settings.py`, `app/ai/client.py`).
- Introduced an in-memory log buffer and `/api/logs` endpoints to surface recent application logs in the Health & Logs tab (`app/utils/log_buffer.py`, `app/utils/logging.py`, `app/web/api/logs.py`).
- Rebuilt the frontend admin into dashboard/newsletters/health/global settings views with Vite output dropped into `app/web/static`. Major additions include the redesigned newsletter form with timezone dropdowns, the model configuration controls, and responsive theming (`frontend/src/pages/*`, `frontend/src/components/NewsletterForm.tsx`, `frontend/src/lib/api.ts`, `frontend/src/styles.css`, `frontend/vite.config.ts`).
- Backend health endpoint now reports scheduler jobs, run summaries, and newsletter schedule metadata to power the dashboard cards (`app/web/api/status.py`).
- Resolved newsletter update failures by coercing feed `HttpUrl` values to plain strings before persisting, fixing the 500 error when saving edits (`app/data/repositories.py`).
- 2025-09-17: Fixed newsletter edit regression by wiring `includeWatchlist` state through `NewsletterForm` (instead of the undefined `include_watchlist` identifier), refreshed the Vite bundle, and confirmed updates via headless Playwright flow (`frontend/src/components/NewsletterForm.tsx`, `frontend/src/pages/NewslettersPage.tsx`, `app/web/static/assets/index-CDerOtoi.js`).
- Verified builds and runtime assets with `python3 -m compileall app` and `npm run build` after each backend/frontend change.
- Captured per-run log output in `run_logs` table, added `/api/logs?run_id=` for archived retrieval, and exposed UI selector + styles in the Health & Logs view (`app/tasks/service.py`, `app/data/models.py`, `app/data/repositories.py`, `app/web/api/logs.py`, `frontend/src/pages/HealthPage.tsx`).
- Updated OpenAI GPT-5 requests to use `max_completion_tokens` and improved error surfacing; added unit coverage (`app/ai/client.py`, `tests/test_ai_client.py`).
- Refreshed Health dashboard metrics and scheduler list: auto-refreshing snapshot, new Runs/Failures counters, and simplified job cards (`frontend/src/pages/HealthPage.tsx`, `frontend/src/styles.css`, `app/web/api/status.py`).
- Fixed dashboard health status false positives by updating status logic to only show "Attention Needed" for consecutive failures or ongoing issues rather than historical failures; added specific status_details array to provide clear reasons for status changes (`app/web/api/status.py`, `frontend/src/pages/DashboardPage.tsx`).
- Resolved OpenAI gpt-5-mini model fallback issues by updating API parameters to use `max_completion_tokens` instead of `completion_tokens`, removing temperature/top_p parameters for gpt-5 models, and updating with fresh API key (`app/ai/client.py`, `.env`).
- Fixed RSS feed ingestion failures due to redirects by adding `follow_redirects=True` to httpx client configuration (`app/ingest/rss.py`).
- Corrected email recipient handling to use current database settings instead of cached environment values by implementing dynamic settings loading in pipeline execution (`app/tasks/pipeline.py`, `app/config/settings.py`, `app/web/api/schemas.py`).
- Enhanced AI prompt formatting by adding explicit instruction to prevent newsletters from ending with questions, ensuring factual conclusions only (`app/prompts/format_instructions.md`).
- Implemented auto-generated unique newsletter slugs with conflict resolution to eliminate 500 errors during creation; made slug field read-only with live updates as user types newsletter name (`app/web/api/newsletters.py`, `frontend/src/components/NewsletterForm.tsx`).
