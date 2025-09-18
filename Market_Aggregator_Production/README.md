AI Market Intel (Cloudflare-first)

This repo scaffolds a minimal-but-solid workflow for a twice-daily market news digest using Cloudflare Workers, D1, KV, Resend, and Gemini 2.5 Flash. It includes a Pages-based admin UI (React) and GitHub Actions deploy.

Key features implemented in the Worker skeleton:
- Cron + on-demand `/cron` route
- Concurrent RSS fetch with bounded concurrency and per-feed safe-fail
- De-dupe via normalized `content_hash`
- Selection by freshness + watchlist overlap
- Summarization via Gemini with fallback
- Email via Resend with safe HTML template
- Persistence of runs, articles, seen hashes, and digest HTML
- Health endpoints: `/health` and `/latest`

What’s included
- Cloudflare Worker (TypeScript) under `apps/worker`
- Cloudflare Pages (Vite + React) starter under `apps/admin-ui`
- D1 schema under `db/schema.sql` (+ `migrations/` placeholder)
- Prompt stub under `prompts/summarize_v1.md`
- GitHub Actions deploy workflow under `.github/workflows/deploy.yml`

Notes and small deviations from the outline
- The schema stores the final rendered digest HTML in a new `digests` table keyed by `run_id` (the outline mentions archiving HTML but didn’t include a table). This keeps large HTML blobs out of `runs`.
- Cron timezone: Cloudflare cron strings are in UTC. If your account supports timezone-aware schedules in wrangler, you can add `timezone = "America/Denver"`. Otherwise, choose UTC times that approximate 06:30 / 17:30 MT and adjust seasonally.
- Admin routes include a simple Access check that trusts `Cf-Access-Authenticated-User-Email` (works behind Cloudflare Access). In local dev, set `DEV_MODE=1` to bypass.

Quick start (high level)
- Create Cloudflare resources:
  - D1 database (bind it as `DB`)
  - KV namespace (bind as `MARKET_FLAGS`)
  - Access (Zero Trust) policy for admin UI and `/admin/*` APIs
- Configure secrets in Worker:
  - `wrangler secret put RESEND_API_KEY`
  - `wrangler secret put GEMINI_API_KEY`
  - `wrangler secret put FINNHUB_API_KEY` (for market performance quotes)
- Apply schema to D1 (from `db/schema.sql`).
- Set initial settings via admin UI (or insert into `settings`).
- Configure cron triggers in `wrangler.toml` and deploy.

GitHub Actions & OIDC
- The workflow uses `cloudflare/wrangler-action@v3`. Prefer OIDC if your Cloudflare account is configured for it; otherwise, use a narrowly scoped API token via `CLOUDFLARE_API_TOKEN`.

Local notes
- This project targets Cloudflare; it doesn’t depend on server-side Node. The Worker builds with Wrangler. The UI builds with Vite and deploys to Pages.

Initial SQL for settings (example)
```
INSERT INTO settings(key, value) VALUES
  ("digest_times", '["06:30","17:30"]'),
  ("recipient_emails", '["you@example.com"]'),
  ("max_concurrency", '6'),
  ("max_articles_considered", '60'),
  ("max_articles_for_ai", '25'),
  ("watchlist", '["SPY","QQQ","IWM","GLD","BTC","UUP"]');
```

Local dev tips
- Use `wrangler d1 execute <DB_NAME> --file=./db/schema.sql` to apply schema.
- Ensure `FINNHUB_API_KEY` is set before testing market data integration.
- Add a few feeds into `feeds` (e.g. major finance RSS URLs).
- Start the Worker locally with `wrangler dev` inside `apps/worker`.
- The UI can be previewed with `npm run dev` in `apps/admin-ui`.
