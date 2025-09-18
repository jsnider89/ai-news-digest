# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Market Intel is a Cloudflare-first market news digest system that aggregates RSS feeds twice daily, de-duplicates content, selects relevant articles based on watchlists, summarizes using AI, and sends email digests.

## Architecture

**Tech Stack:**
- Cloudflare Workers (TypeScript) - main orchestration
- Cloudflare D1 (SQLite) - data persistence  
- Cloudflare KV - feature flags and circuit breaker state
- Cloudflare Pages - React admin UI
- Cloudflare Access - authentication for admin endpoints
- Resend - email delivery
- Gemini AI - content summarization

**Core Components:**
- `apps/worker/src/index.ts` - main routes (/cron, /health, /latest, /admin/api/*)
- `apps/worker/src/ingest.ts` - RSS feed fetching with bounded concurrency
- `apps/worker/src/select.ts` - article ranking by freshness + watchlist overlap
- `apps/worker/src/summarize.ts` - Gemini AI integration with fallbacks
- `apps/worker/src/email.ts` - Resend integration with HTML templates
- `apps/worker/src/storage.ts` - D1 database operations
- `apps/admin-ui/` - React dashboard for viewing feeds, settings, runs

**Data Flow:**
1. Cron triggers orchestrate runs twice daily
2. Concurrent RSS fetch with safe-fail (bounded concurrency: 6)
3. De-duplicate using SHA-256 content hash (title + URL + date + source)
4. Select articles by freshness (24h) + watchlist hits (+5 score each)
5. Summarize top articles via Gemini with provenance-first prompting
6. Email digest via Resend, persist HTML to D1

## Development Commands

**Worker Development:**
```bash
cd apps/worker
wrangler dev                    # Local development server
wrangler publish               # Deploy to Cloudflare
wrangler d1 execute DB_NAME --file=../../db/schema.sql  # Apply schema
wrangler secret put RESEND_API_KEY     # Set email API key
wrangler secret put GEMINI_API_KEY     # Set AI API key
```

**Admin UI Development:**
```bash
cd apps/admin-ui
npm install                    # Install dependencies
npm run dev                    # Local development server
npm run build                  # Build for production
```

**Testing Endpoints:**
- `GET /health` - Latest run metadata
- `GET /latest` - Latest digest HTML
- `GET|POST /cron` - Manual run trigger
- `GET /admin/api/feeds` - List feeds (Access-protected)
- `GET /admin/api/settings` - Read settings (Access-protected)

## Configuration

**Required Bindings (wrangler.toml):**
- D1 database: `DB` 
- KV namespace: `MARKET_FLAGS`

**Required Secrets:**
- `RESEND_API_KEY` - Email delivery
- `GEMINI_API_KEY` - AI summarization

**Environment Variables:**
- `DEV_MODE` - Set to "1" to bypass Access check locally (never in production)

**Database Settings (D1 settings table):**
- `digest_times` - JSON array: `["06:30","17:30"]`
- `recipient_emails` - JSON array: `["user@example.com"]` 
- `max_concurrency` - String: `"6"`
- `max_articles_considered` - String: `"60"`
- `max_articles_for_ai` - String: `"25"`
- `watchlist` - JSON array: `["SPY","QQQ","IWM","GLD","BTC","UUP"]`

## Key Implementation Details

**De-duplication Strategy:**
- Hash = SHA-256 of: `${clean_title}|${canonical_url}|${date_only}|${source}`
- Uses `seen_hashes` table for fast lookups
- `INSERT OR IGNORE` prevents duplicates in articles table

**Concurrency & Error Handling:**
- Bounded concurrency (default: 6 feeds in parallel)
- Per-request timeout (~10s)  
- Aggregated with `Promise.allSettled` semantics
- Circuit breaker helpers in `util.ts` (not yet integrated)

**AI Integration:**
- Currently targets `gemini-2.0-flash` model (update if unavailable)
- Provenance-first prompting (see `prompts/summarize_v1.md`)
- Fallback to headlines-only digest on AI failure
- Run marked as `partial` when AI fails

**Security:**
- Admin endpoints protected by Cloudflare Access
- Checks `Cf-Access-Authenticated-User-Email` header
- Never commit secrets - use `wrangler secret put`
- Log redaction for tokens ≥20 chars

## Database Schema

Core tables: `feeds`, `articles`, `seen_hashes`, `runs`, `run_articles`, `settings`, `digests`

## Git & GitHub Integration

**Authentication Setup:**
- GitHub Personal Access Token stored in `~/.bashrc`:
  - `GITHUB_USERNAME="jsnider89"`  
  - `GITHUB_TOKEN="ghp_..."` (configured for this server)
- Remote repository: `https://github.com/jsnider89/Market_Aggregator_Production.git`
- Git remote URL includes embedded token for automated pushes

**Git Commands for Claude Code:**
```bash
git push                       # Push changes (auth configured)
git status                     # Check working directory status
git add .                      # Stage all changes
git commit -m "message"        # Create commit with message
```

## Deployment

GitHub Actions workflow deploys both Worker and Pages:
- Requires `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` secrets
- Worker deploys from `apps/worker/`
- Pages deploys from `apps/admin-ui/dist` to project `ai-market-intel-admin`

## Current Status (As of 2025-09-05)

✅ **FULLY OPERATIONAL** - Complete end-to-end market intelligence system

**Live URLs:**
- Worker API: `https://ai-market-intel-worker.jonsnider.workers.dev`
- Admin UI: `https://7b80e088.ai-market-intel-admin.pages.dev`

**Deployed Features:**
- ✅ Complete RSS feed ingestion and processing (4 feeds configured)
- ✅ AI-powered content summarization via Gemini
- ✅ Twice-daily automated cron scheduling (12:30 & 23:30 UTC)  
- ✅ Cloudflare Access authentication for admin endpoints
- ✅ Full CRUD admin interface for feeds and settings management
- ✅ CORS-enabled cross-origin API access
- ✅ User-friendly settings UI (no JSON editing required)

**Admin Interface Features:**
- 📊 **Dashboard**: System health, latest runs, manual trigger
- 📡 **Feeds Management**: Add/edit/delete/enable/disable RSS feeds  
- ⚙️ **Settings**: Email recipients, digest times, watchlist, processing limits
- 🔐 **Security**: Protected by Cloudflare Access with email-based policies

**Secrets Configured:**
- ✅ `RESEND_API_KEY` - Email delivery service
- ✅ `GEMINI_API_KEY` - AI summarization service

**Database:**
- ✅ D1 schema applied to both local and remote instances
- ✅ Settings and feeds seeded with initial data
- ✅ All tables operational with proper indexing

**Testing Status:**
- ✅ Manual digest generation working (60 articles processed, 25 used for AI)
- ✅ Cross-origin API calls from admin UI functional
- ✅ Feed enable/disable toggle working correctly
- ✅ Settings save/update operations working
- ✅ Digest 401 authorization fixed - digest links now publicly accessible
- ✅ Email delivery working with verified domain

**Recent Changes (2025-09-05):**
- ✅ Added Finnhub market data client and per-run persistence (`market_data`)
- ✅ Reworked Gemini prompt to structured 3-section report; increased token budget
- ✅ Email template enhanced with Market Performance table + AI summary output
- ✅ Selection logic updated to ignore watchlist and favor source diversity

Notes:
- Add secret `FINNHUB_API_KEY` and apply DB schema to use new features.
- See IMPLEMENTATION_TASKS.md for roll-out steps.

## Admin API Endpoints

All admin endpoints require Cloudflare Access authentication:

**Read Endpoints:**
- `GET /admin/api/feeds` - List all feeds (enabled + disabled)
- `GET /admin/api/settings` - Get system settings

**Write Endpoints:**
- `POST /admin/api/feeds` - Add new RSS feed
- `PUT /admin/api/feeds/{id}` - Update existing feed  
- `DELETE /admin/api/feeds/{id}` - Delete feed
- `PUT /admin/api/settings` - Update system settings
