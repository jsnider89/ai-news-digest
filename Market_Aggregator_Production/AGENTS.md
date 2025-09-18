AI Market Intel – Agent Notes

Purpose
- Capture architecture, decisions, setup, and next steps for the Cloudflare-first market digest system.
- Enable quick handoff: what exists, how to run/deploy, and what to build next.

High-Level Flow
- Twice daily cron (Cloudflare Worker) orchestrates a run:
  1) Read settings from D1 (and feature flags from KV if used).
  2) Concurrently fetch RSS/Atom feeds with bounded concurrency, safe-fail.
  3) Normalize + de-dupe using a deterministic content_hash.
  4) Select top items by freshness with source diversity (watchlist no longer affects ranking).
  5) Summarize via Gemini (fallback to headlines-only on failure).
  6) Email digest via Resend.
  7) Persist run metadata and digest HTML; expose health/latest endpoints.

Tech Stack
- Cloudflare Workers: orchestrator + fetch/dedupe/select/summarize/email endpoints.
- Cloudflare Cron Triggers: schedule runs.
- Cloudflare D1 (SQLite): feeds, articles, runs, run_articles, settings, seen_hashes, digests.
- Cloudflare KV: fast feature flags / circuit breaker state.
- Cloudflare Pages: minimal React admin UI (read-only for now).
- Cloudflare Access: protect /admin/* and write APIs (UI trusts Cf-Access headers).
- Resend: email delivery.
- Gemini: AI summarization (provenance-first prompt).

Repo Layout
```
ai-market-intel/
├─ apps/
│  ├─ worker/
│  │  ├─ src/
│  │  │  ├─ index.ts       # routes: /cron, /health, /latest, /admin/api/*
│  │  │  ├─ ingest.ts      # bounded RSS fetch + simple XML parsing
│  │  │  ├─ dedupe.ts      # normalization + SHA-256 content_hash
│  │  │  ├─ select.ts      # ranking by freshness + source diversity (no watchlist bias)
│  │  │  ├─ summarize.ts   # Gemini call; markdown→safe HTML; fallback
│  │  │  ├─ email.ts       # Resend integration + HTML template
│  │  │  ├─ storage.ts     # D1 accessors (runs, articles, settings, digests)
│  │  │  └─ util.ts        # logger, hash, p-limit, timeout, circuit helpers
│  │  └─ wrangler.toml     # D1/KV bindings + cron triggers
│  └─ admin-ui/            # Cloudflare Pages (Vite + React)
│     ├─ src/
│     │  ├─ pages/App.tsx  # Dashboard, Feeds, Settings (read-only)
│     │  └─ lib/api.ts     # calls Worker API
│     ├─ index.html
│     ├─ package.json
│     └─ vite.config.ts
├─ db/
│  ├─ schema.sql           # D1 schema (tables + indexes)
│  └─ migrations/.gitkeep
├─ prompts/
│  └─ summarize_v1.md      # provenance-first prompt stub
├─ .github/
│  └─ workflows/deploy.yml # Worker + Pages deploy
└─ README.md
```

Bindings & Secrets
- D1 database binding: `DB`
- KV namespace binding: `MARKET_FLAGS`
- Secrets (Wrangler):
  - `RESEND_API_KEY`
  - `GEMINI_API_KEY`
- Vars:
  - `DEV_MODE` (string "0"/"1"), bypasses Access check locally.

Cron
- Configured in `apps/worker/wrangler.toml` under `[triggers]`:
  - `crons = ["30 12 * * *", "30 23 * * *"]` (UTC placeholders for 06:30 / 17:30 MT during DST).
  - If your account supports timezones, add `timezone = "America/Denver"` and adjust.

Endpoints (Worker)
- `GET /health`: returns latest run metadata.
- `GET /latest`: returns the latest saved digest HTML.
- `GET|POST /cron`: manual run trigger (same logic as scheduled run).
- `GET /admin/api/feeds`: list enabled feeds (Access-protected; `Cf-Access-Authenticated-User-Email`).
- `GET /admin/api/settings`: read important settings keys.

Settings (D1 `settings` table; JSON strings where arrays)
- `digest_times`: e.g., `["06:30","17:30"]`
- `recipient_emails`: e.g., `["you@example.com"]`
- `max_concurrency`: e.g., `"6"`
- `max_articles_considered`: e.g., `"60"`
- `max_articles_for_ai`: e.g., `"25"`
- `watchlist`: e.g., `["SPY","QQQ","IWM","GLD","BTC","UUP"]`

Schema (D1)
- `feeds(id, name, url, category, enabled, added_at)`
- `articles(id, content_hash, source, title, canonical_url, published_at, first_seen_at)`
- `seen_hashes(content_hash, first_seen_at)`
- `runs(run_id, started_at, finished_at, status, feeds_total, feeds_ok, articles_seen, articles_used, ai_tokens_in, ai_tokens_out, email_sent)`
- `run_articles(run_id, article_id, rank, score)`
- `settings(key, value)`
- `digests(run_id, html, created_at)`

De-dupe Strategy
- content_hash = sha256(f"{title_clean}|{canonical_url}|{published_at_date_only}|{source}")
  - `title_clean`: lowercase, strip punctuation/space to single spaces.
  - `canonical_url`: normalized URL, drop UTM and common tracking params.
  - `published_at_date_only`: ISO date (YYYY-MM-DD) or null.
  - `source`: hostname only.
- Insert into `seen_hashes`; `articles` insert is `INSERT OR IGNORE` by hash.
- Optional near-dup detection (Jaccard on titles) is not yet implemented.

Ingestion & Concurrency
- Bounded concurrency via a small p-limit implementation (default 6).
- Per-request timeout ~10s; results aggregated with `Promise.allSettled` semantics.
- Simple regex-based RSS/Atom parsing (best effort). Consider a more robust XML parser later.

Selection
- Score = freshness (within 24h) with simple source diversity cap.
- Top N for AI (`max_articles_for_ai`), selection applied to newly observed items this run.

Summarization (Gemini)
- Endpoint: Generative Language API `.../models/gemini-2.0-flash:generateContent` in code.
  - Note: Model IDs evolve; adjust to currently available model (e.g., `gemini-1.5-flash`).
- Prompt: provenance-first (see `prompts/summarize_v1.md`).
- Fallback: headlines-only HTML when AI call fails; run marked `partial` accordingly.

Email (Resend)
- Safe HTML template with escaped content and external `Read original` links.
- From address placeholder `digest@yourdomain.com` (configure domain in Resend).

Persistence & Artifacts
- `runs` counts: feeds_total/ok, articles_seen/used, token usage, email_sent.
- `run_articles`: selected article ordering with scores.
- `digests`: currently stores the summary HTML only (NOTE: see TODO below to store full email HTML).

Access & Auth
- Admin endpoints rely on Cloudflare Access; Worker checks `Cf-Access-Authenticated-User-Email`.
- Local dev can bypass with `DEV_MODE=1` (do not enable in production).

CI/CD & Git Integration
- GitHub Actions workflow deploys Worker (`wrangler-action@v3`) and Pages (`pages-action`).
- Required repo secrets: `CLOUDFLARE_ACCOUNT_ID`; prefer OIDC; otherwise `CLOUDFLARE_API_TOKEN` with minimal scope.
- Pages project name: `ai-market-intel-admin` (can be changed).
- **GitHub Authentication**: Personal Access Token configured in `~/.bashrc` on server:
  - `GITHUB_USERNAME="jsnider89"`
  - `GITHUB_TOKEN="ghp_..."` (full token stored securely)
  - Remote URL: `https://github.com/jsnider89/Market_Aggregator_Production.git` with embedded auth
- **Git Commands for AI**: Standard git operations work automatically (`git push`, `git status`, etc.)

Local Development
- Apply schema: `wrangler d1 execute <DB_NAME> --file=./db/schema.sql`
- Seed settings (example):
  ```sql
  INSERT INTO settings(key, value) VALUES
    ("digest_times", '["06:30","17:30"]'),
    ("recipient_emails", '["you@example.com"]'),
    ("max_concurrency", '6'),
    ("max_articles_considered", '60'),
    ("max_articles_for_ai", '25'),
    ("watchlist", '["SPY","QQQ","IWM","GLD","BTC","UUP"]');
  ```
- Add some feeds (examples; replace as desired):
  ```sql
  INSERT INTO feeds(name, url, category, enabled) VALUES
    ("WSJ Markets", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "markets", 1),
    ("Reuters Business", "https://www.reuters.com/markets/us/rss", "business", 1),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex", "finance", 1),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "crypto", 1);
  ```
- Run Worker locally in `apps/worker`: `wrangler dev`
- Run UI locally in `apps/admin-ui`: `npm install && npm run dev`

Operational Notes
- Logging: JSON logs with basic redaction of ≥20 char tokens to avoid secrets leakage.
- Failure modes:
  - Feed failures → run `partial`, still emails and persists digest.
  - AI failure → fallback headlines-only digest; `partial`.
  - Email failure → digest HTML still saved; next run can reference missed digest.
- Circuit breaker: helpers exist in `util.ts` using KV (`cb:<host>` with TTL). Not yet integrated into `ingest` flow (see TODO).

## COMPLETED - 2025-09-05 Session

✅ **Production Deployment Complete** - System fully operational
✅ **Admin Write APIs** - Full CRUD operations for feeds and settings implemented
✅ **Cloudflare Access Integration** - Admin UI secured with email-based policies  
✅ **CORS Configuration** - Cross-origin requests working between Pages and Workers
✅ **User-Friendly Admin Interface** - No JSON editing required, intuitive form-based UI
✅ **Database Setup** - D1 schema applied, settings seeded, feeds configured
✅ **API Key Configuration** - Both Resend and Gemini keys deployed securely
✅ **Feed Management** - Add/edit/delete/enable/disable with proper visibility

**Live System URLs:**
- **Worker API**: `https://ai-market-intel-worker.jonsnider.workers.dev`
- **Admin UI**: `https://fb634997.ai-market-intel-admin.pages.dev`

**Admin Interface Features Implemented:**
- **Dashboard**: System status, health monitoring, manual run triggering with detailed results
- **Feeds**: Complete CRUD with enable/disable toggle (shows all feeds)
- **Settings**: User-friendly forms for emails, times, watchlist, processing limits
- **Authentication**: Cloudflare Access with cross-domain API authorization
- **Manual Run**: User-friendly execution with loading states and detailed result summaries

**Technical Improvements Made:**
- Added `getFeeds()` vs `getEnabledFeeds()` separation for admin vs processing
- Implemented proper CORS headers for cross-origin requests
- Added success/error messaging for all user operations
- Fixed authentication flow for Pages → Worker API calls
- Enhanced manual run UI with loading states and detailed result reporting
- Replaced raw JSON responses with user-friendly dialog messages

## Remaining TODOs (Future Enhancements)

- Circuit breaker integration in `ingest`: pause hosts after N failures for 15 minutes.
- Archive UI: list `runs` and view stored digest by `run_id`.
- Store full email HTML in `digests` (currently stores summary section only).
- Better RSS parsing: replace regex parser with robust XML handling.
- Tests: unit tests for de-dupe and parsing fixtures; minimal e2e for run path.
- Cron timezone: add `timezone` in `wrangler.toml` if available; otherwise adjust UTC for DST changes.
- Observability: structured logs with `run_id`, feed latency, and counts; optional Logpush / analytics.
- Email allowlist validation in Access JWT claims.

Security
- No secrets in repo. Use `wrangler secret` for `RESEND_API_KEY` and `GEMINI_API_KEY`.
- GitHub → Cloudflare uses OIDC (preferred) or a minimal API token.
- Admin endpoints require Cloudflare Access; never set `DEV_MODE=1` in production.

Model Notes (Gemini)
- The code currently targets `gemini-2.0-flash:generateContent` endpoint. If unavailable in your account/region, use a supported model id (e.g., `gemini-1.5-flash`) and update `summarize.ts`.

## Ownership & System Status

🎉 **SYSTEM FULLY OPERATIONAL** - Complete market intelligence platform deployed and functional.

**Current Status:**
- ✅ **Production Ready**: End-to-end digest generation working
- ✅ **Admin Interface**: Complete self-service management UI  
- ✅ **Authentication**: Cloudflare Access securing all admin operations
- ✅ **Automation**: Twice-daily cron execution (12:30 & 23:30 UTC)
- ✅ **Monitoring**: Health endpoints and manual trigger capability

**For Next Development Cycle:**
1. **Enhanced Features**: Archive UI for historical runs and digests
2. **Reliability**: Circuit breaker integration for problematic feeds  
3. **Observability**: Structured logging and analytics integration
4. **Testing**: Unit and integration test coverage
5. **Content**: Expand RSS feed sources and fine-tune AI prompts

**System Maintenance:**
- No regular maintenance required - fully serverless
- Monitor email delivery through Resend dashboard
- Adjust watchlist and recipient emails through admin UI as needed
- Add/remove RSS feeds through admin interface
