# Combined Aggregator Integration Plan

## 1. Goals & Scope
- Deliver a single-container Python stack that merges the ingestion/AI/email pipeline from `AI-Market-Aggregator-New` with the dashboard and persistence ideas from `Market_Aggregator_Production`.
- Support multiple newsletters with per-newsletter feeds, schedules, prompts, and watchlists while sharing global AI/email/configuration.
- Provide a responsive React dashboard (mobile friendly) for monitoring, manual runs, resets, and newsletter management.
- Ensure reliable RSS → AI → email execution with configurable provider order (OpenAI, Gemini, Anthropic) and Resend delivery.
- Package everything for easy redeploy on Linux servers, with persistent SQLite state living under `/data`.

## 2. Source Repo Feature Inventory
### AI-Market-Aggregator-New (Python)
- Strengths: modular RSS ingest, multi-provider LLM client with fallback, Finnhub integration, HTML email generator, orchestrator script, pytest suite.
- Gaps to carry forward: lacks web UI, single newsletter flow, limited persistence.

### Market_Aggregator_Production (Cloudflare)
- Strengths: scheduler concepts, RSS concurrency, dedupe/watchlist logic, React admin dashboard, run history endpoints.
- Gaps: Cloudflare-targeted runtime (Workers + D1/KV), TypeScript serverless patterns not directly reusable in Python container.

## 3. Target Repository Layout
```
app/
  ai/            # provider registry, prompt assembly, fallback logic
  config/        # settings management, .env loading, data validation
  data/          # SQLAlchemy models, CRUD services, migrations bootstrap
  email/         # Resend client wrapper, email rendering
  ingest/        # RSS + market data clients, dedupe helpers
  tasks/         # scheduler jobs (process_newsletter_task, reset logic)
  web/
    api/         # FastAPI routers for newsletters, runs, settings
    templates/   # (optional) fallback templates
    static/      # React build output
    main.py      # FastAPI app + scheduler startup
  cli.py         # helper commands (create newsletter, run once)

app/ai/prompts/
  base_prompt.txt
  format_instructions.txt
  system_message.txt

data/
  migrations/    # Alembic scripts
  seeds/         # optional bootstrap JSON

frontend/        # React admin source (ported from admin-ui)
requirements.txt
package.json     # for frontend build (if monorepo style)
Dockerfile
INTEGRATION_PLAN.md
```

## 4. Data Model Plan (SQLite via SQLAlchemy)
- `newsletters`: id (PK), slug, name, description, custom_prompt, schedule_config (JSON storing times per day), timezone (defaults to host zone), include_watchlist (bool), created_at, updated_at, active.
- `newsletter_feeds`: id, newsletter_id (FK), url, title (optional), category, order_index.
- `newsletter_watchlists`: id, newsletter_id, symbol (uppercased), maybe tags for grouping.
- `runs`: id, newsletter_id, status, started_at, finished_at, articles_processed, ai_provider_used, error_message.
- `digests`: id, run_id, html_content, subject_line, summary_metadata.
- `seen_hashes`: id, newsletter_id, content_hash, first_seen, last_seen.
- Settings approach:
  - Global settings table (`global_settings` key/value) or Pydantic settings persisted via JSON for AI provider order, Resend sender info, email formatting lock, default schedule.
  - Keep locked prompt fragments on disk; only newsletter `custom_prompt` stored in DB.

## 5. Scheduler & Execution Flow
1. On startup, load global settings (including default timezone using `zoneinfo.ZoneInfo`. If not set, derive from host machine and store).
2. Initial migration via Alembic or custom bootstrap script runs automatically.
3. APScheduler (BackgroundScheduler) registers a job that polls active newsletters, computing next run windows from stored times (e.g., ["06:30", "17:30"]). Each scheduled run enqueues `process_newsletter_task(newsletter_id)`.
4. Manual actions from the dashboard call FastAPI endpoints:
   - `/api/newsletters/{id}/run` triggers the same task immediately.
   - `/api/newsletters/{id}/reset?hours=24` clears runs/digests/seen hashes in that window before optionally re-running.
5. `process_newsletter_task` steps:
   - Fetch newsletter definition, feeds, and watchlist.
   - RSS aggregator pulls articles with concurrency limit, dedupe via `seen_hashes`, apply watchlist filters if enabled.
   - Compose AI prompt: `system_message + base_prompt + format_instructions + newsletter.custom_prompt + run_context` (articles, watchlist, schedule info).
   - Multi-provider AI client executes with configured cascade.
   - Resend email is generated from locked template + AI result; recipients drawn from global settings (possibly newsletter-specific CC list later).
   - Persist run + digest status; update dashboard caches.
6. Health endpoints (`/health`, `/api/status/latest`) expose aggregated metrics for dashboards.

## 6. React Dashboard Enhancements
- Keep React app (moved to `frontend/`) and update build tooling (Vite or CRA) to output static files consumed by FastAPI.
- Navigation: Overview (system health), Newsletters, Global Settings, Logs.
- **Newsletters page**:
  - Cards/list view with responsive layout; each card shows schedule, last run, next run, status, watchlist indicators.
  - Actions: Run Now, Reset 24h, Edit, Toggle Active.
  - “Create Newsletter” wizard: step 1 name/description; step 2 feeds (URL entry + list); step 3 schedule (time picker for multiple local-time entries); step 4 watchlist toggle + chips input; step 5 custom prompt textarea with read-only preview of locked formatting instructions.
- **Global Settings page**:
  - Manage AI provider order and default model; display API key presence (not raw values).
  - Resend sender details and fallback email.
  - Default schedule times (affects new newsletters).
  - Timezone selector (default to host timezone, allow override from list of Olson zones).
- UI must adapt to mobile (<=768px): stack cards, use drawer modals, avoid wide tables.
- API integration through fetch/axios with auth placeholder (future expansion).

## 7. Docker & Deployment Strategy
- Multi-stage Dockerfile:
  1. `node:20-alpine` installs `frontend/` deps, builds React bundle.
  2. `python:3.11-slim` installs system deps (build-essential, libpq if needed), copies backend code and built `frontend/dist` into `app/web/static`.
  3. Install `requirements.txt` (includes FastAPI, SQLAlchemy, APScheduler, Resend SDK, feedparser, etc.).
  4. Copy Alembic scripts / migrations and entrypoint script.
  5. Entry command: `python -m app.tasks.prestart && uvicorn app.web.main:app --host 0.0.0.0 --port 8000` (prestart handles migrations/seeding).
- Expose port 8000; declare `/data` volume for SQLite & logs.
- Provide sample `docker run` and optional `docker-compose.yml` for development (bind mounts for hot reload optional).

## 8. Testing Roadmap
- Pytest structure mirrors `app/` modules (`tests/ingest`, `tests/ai`, etc.).
- Unit tests: AI provider fallback ordering, prompt assembly, feed dedupe, watchlist parsing, scheduler next-run calculations.
- Integration tests: fake RSS + fake LLM + fake Resend to verify pipeline writes DB and triggers email body.
- API tests: newsletter CRUD, run/reset endpoints, global settings updates, mobile-specific data responses (if variant).
- Frontend tests: component/unit tests with Vitest/React Testing Library for newsletter wizard; optional Playwright/Cypress smoke for responsive layout.

## 9. Implementation Phases
1. **Bootstrap repo**: create `app/`, copy/import existing Python modules, set up Poetry or pip requirements, configure Pydantic settings, initialize Alembic.
2. **Data layer**: implement SQLAlchemy models, migrations, repository functions, and CLI seeds.
3. **Scheduler & tasks**: wire APScheduler, implement `process_newsletter_task`, watchlist parsing, Resend integration.
4. **API & web**: build FastAPI routers, mount React app, add health endpoints.
5. **Frontend migration**: port `admin-ui`, adjust build path, implement newsletter wizard, mobile responsiveness.
6. **Dockerization**: craft multi-stage Dockerfile, entry scripts, documentation, sample `.env`.
7. **Testing & polish**: extend pytest suite, add frontend tests, write docs for configuration and operations.

## 10. Outstanding Questions / Follow-ups
- Authentication strategy for dashboard (initial assumption: local trusted access; revisit if multi-user needed).
- Handling of Finnhub or other market data (global watchlist vs. per newsletter detail) — confirm if still required.
- Email recipients: currently assumed to live in global settings; future per-newsletter override optional.

_Last updated: 2024-XX-XX. Update this document as milestones complete or scope changes._

## 11. Progress Log
- Initial backend scaffolding, newsletter scheduler, API routes, and multi-provider pipeline implemented.
- React dashboard migrated with management UI for newsletters, run history, and settings.
- Added scheduler-backed run persistence, run digests, and Docker build pipeline.
- Implemented newsletter CRUD via API/UI with per-newsletter feeds, prompts, watchlists, and active toggle.
