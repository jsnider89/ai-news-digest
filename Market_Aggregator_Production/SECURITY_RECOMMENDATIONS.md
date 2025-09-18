# Security Recommendations

This document summarizes opportunities to harden the AI Market Intel system across authorization, data handling, third‑party API use, and operational controls.

## Authorization & Access Control

- Admin endpoints: Require Cloudflare Access for all `/admin/api/*` routes, including `/cron` manual trigger.
  - Current: most admin routes enforce Access; `/cron` is public. Recommendation: protect `/cron` via Access (or separate a public, read‑only status route).
  - Consider removing Origin‑based allow logic in production; rely exclusively on Cloudflare Access.
- Public endpoints: `/latest` and `/admin/api/runs/:id/digest` are public by design. Ensure these never include secrets or internal logs.
  - Current rendering uses safe HTML and escapes user/content fields.

## CORS & CSRF

- CORS: Restrict to a single Pages origin via `ALLOWED_ORIGIN`. Avoid wildcards in production.
- CSRF: Admin UI uses cookies (credentials: include). Add CSRF token for write endpoints (e.g., `/admin/api/settings`, feed CRUD, reset‑seen), or rely strictly on Access with “Require JWT” semantics.

## Input Validation & Settings

- Settings upsert: The write handler accepts arbitrary keys. Restrict to an allowlist and validate value types to prevent accidental misconfiguration.
- Feeds: Validate URLs and consider an allowlist by domain to avoid SSRF. Ingress fetches remote XML; even with tight timeouts, malformed endpoints can cause resource usage.

## Secrets & Logging

- Secrets: Continue using `wrangler secret` for API keys. Do not echo secrets in logs.
- Redaction: Log redaction masks 20+ char tokens. Keep it in place and avoid logging headers/bodies from provider calls.
- Per‑run logs: Now include per‑feed outcomes and AI provider/tokens. Avoid storing full prompts or model outputs in logs.

## Third‑Party APIs

- Resend: Verify sender domain and enforce a fixed `from` address in settings to prevent spoofing via UI.
- Gemini/OpenAI/Anthropic: Use exponential backoff (implemented). Add circuit breaking if repeated failures occur to reduce cost/pressure.
- Finnhub: Rate‑limit calls (sequential fetch implemented). Consider caching quotes for brief intervals to avoid bursts.

## Data Sanitization & XSS

- Digest content: Markdown conversion escapes HTML; links are escaped; headings and lists are whitelisted. Continue to avoid injecting raw HTML from models.
- Email HTML: All styles are inline; avoid user‑controlled content in attributes. Keep escaping enabled for titles/links.

## Availability & Abuse Controls

- `/cron`: Rate‑limit manual trigger or protect with Access.
- Circuit breaker: Integrate the existing KV circuit breaker into ingestion to pause failing hosts for 15 minutes.
- Concurrency & timeouts: Keep bounded concurrency (6 default) and ~10s timeouts for feeds; consider retries with jitter for transient fetch failures.

## Storage & Persistence

- D1 schema: Ensure `digests` stores only rendered HTML. Avoid storing raw prompts/model outputs.
- Settings migration: When new settings are added, provide a migration guide and defaults; reject unexpected keys on write.

## Observability & Alerts

- Consider alerting on repeated AI/email failures or zero‑article runs.
- Consider adding a dashboard view of per‑feed error rates to identify problematic sources quickly.

## Deployment & Configuration

- Remove `triggers.timezone` from wrangler.toml if unsupported to avoid confusion; schedule in UTC or set via dashboard if available.
- Lock down `ALLOWED_ORIGIN` in production to your Pages domain.

## Summary of Concrete Action Items

1. Protect `/cron` with Cloudflare Access (no public access).
2. Restrict settings updates to an allowlist and validate types server‑side.
3. Enforce `ALLOWED_ORIGIN` and rely on Access; remove origin fallback in production.
4. Integrate circuit breaker in `ingest` to pause failing feeds.
5. Add CSRF token on write endpoints if continuing to allow cookie credentials beyond Access headers.
6. Add domain allowlist or validation for feed URLs to reduce SSRF risk.
7. Remove `triggers.timezone` if not supported; ensure schedules are unambiguous.
8. Add basic alerts for repeated AI/email failures.

