import { log, nowIso, parseJsonArray } from "./util";
import type { Env } from "./util";
import { fetchFeeds } from "./ingest";
import { normalizeAndHash, RawItem } from "./dedupe";
import { rankItems } from "./select";
import { summarizeWithGemini, summarizeWithAI, STRUCTURED_PROMPT } from "./summarize";
import { sendDigestEmail } from "./email";
import { fetchMarketData } from "./market-data";
import {
  addRunArticle,
  getFeeds,
  getEnabledFeeds,
  getLatestDigestHtml,
  getLatestRun,
  getSettings,
  getRuns,
  getRunById,
  getDigestHtmlByRun,
  getRunLogs,
  hasSeenHash,
  insertArticle,
  insertSeenHash,
  markRunFinish,
  markRunStart,
  saveDigestHtml,
  addFeed,
  updateFeed,
  deleteFeed,
  upsertSetting,
  appendRunLog,
  saveMarketData,
  resetSeenHashesHours,
  countSeenHashesSince,
} from "./storage";

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // Handle CORS preflight requests
    if (request.method === "OPTIONS") {
      return corsResponse(request, env);
    }

    if (request.method === "GET" && path === "/health") {
      const latest = await getLatestRun(env);
      return json(request, env, { ok: true, latest });
    }

    if (request.method === "GET" && path === "/latest") {
      const html = await getLatestDigestHtml(env);
      if (!html) return new Response("No digest yet", { status: 404 });
      return new Response(html, { headers: htmlHeaders(request, env) });
    }

    if (path === "/cron" && (request.method === "POST" || request.method === "GET")) {
      const res = await runOnce(env);
      return json(request, env, res, res.status === "failed" ? 500 : 200);
    }

    // Admin API stubs (guarded by Access in production)
    if (path === "/admin/api/feeds" && request.method === "GET") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      const feeds = await getFeeds(env);
      return json(request, env, { feeds });
    }
    if (path === "/admin/api/settings" && request.method === "GET") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      const keys = [
        "digest_times",
        "recipient_emails",
        "max_concurrency",
        "max_articles_considered",
        "max_articles_for_ai",
        "watchlist",
        "email_from",
        "per_source_cap",
        "ai_primary",
        "gemini_model_id",
        "openai_model_id",
        "openai_reasoning",
        "summarize_prompt"
      ];
      const settings = await getSettings(env, keys);
      return json(request, env, { settings });
    }

    // Write APIs
    if (path === "/admin/api/feeds" && request.method === "POST") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      try {
        const feed = await request.json();
        const id = await addFeed(env, {
          name: feed.name,
          url: feed.url,
          category: feed.category || null,
          enabled: feed.enabled ?? 1
        });
        return json(request, env, { id, message: "Feed added successfully" });
      } catch (e) {
        return json(request, env, { error: String(e) }, 400);
      }
    }

    if (path.startsWith("/admin/api/feeds/") && request.method === "PUT") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      try {
        const id = parseInt(path.split("/")[4]);
        const updates = await request.json();
        await updateFeed(env, id, updates);
        return json(request, env, { message: "Feed updated successfully" });
      } catch (e) {
        return json(request, env, { error: String(e) }, 400);
      }
    }

    if (path.startsWith("/admin/api/feeds/") && request.method === "DELETE") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      try {
        const id = parseInt(path.split("/")[4]);
        await deleteFeed(env, id);
        return json(request, env, { message: "Feed deleted successfully" });
      } catch (e) {
        return json(request, env, { error: String(e) }, 400);
      }
    }

    if (path === "/admin/api/settings" && request.method === "PUT") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      try {
        const settings = await request.json();
        for (const [key, value] of Object.entries(settings)) {
          await upsertSetting(env, key, typeof value === 'string' ? value : JSON.stringify(value));
        }
        return json(request, env, { message: "Settings updated successfully" });
      } catch (e) {
        return json(request, env, { error: String(e) }, 400);
      }
    }

    // Admin: reset seen hashes for the last N hours
    if (path === "/admin/api/reset-seen" && request.method === "POST") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      try {
        const body = await request.json();
        const hours = Math.max(1, Math.min(168, parseInt(String(body?.hours ?? 12), 10)));
        const before = await countSeenHashesSince(env, hours);
        const deleted = await resetSeenHashesHours(env, hours);
        const after = await countSeenHashesSince(env, hours);
        log({ lvl: "info", msg: "reset-seen", hours, before, deleted, after });
        return json(request, env, { ok: true, hours, before, deleted, after });
      } catch (e) {
        return json(request, env, { ok: false, error: String(e) }, 400);
      }
    }

    // Runs APIs
    if (path === "/admin/api/runs" && request.method === "GET") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      const urlParams = new URL(request.url);
      const limit = Math.max(1, Math.min(200, parseInt(urlParams.searchParams.get("limit") || "50", 10)));
      const runs = await getRuns(env, limit);
      return json(request, env, { runs });
    }
    // Public digest must be handled before generic /runs/:id GET guard
    if (path.startsWith("/admin/api/runs/") && path.endsWith("/digest") && request.method === "GET") {
      const runId = path.split("/")[4];
      const html = await getDigestHtmlByRun(env, runId);
      if (!html) return new Response("Not found", { status: 404 });
      return new Response(html, { headers: htmlHeaders(request, env) });
    }
    if (path.startsWith("/admin/api/runs/") && request.method === "GET") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      const parts = path.split("/");
      const runId = parts[4];
      if (parts.length === 5) {
        const run = await getRunById(env, runId);
        return json(request, env, { run });
      }
    }
    if (path.startsWith("/admin/api/runs/") && path.endsWith("/logs") && request.method === "GET") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      const runId = path.split("/")[4];
      const logs = await getRunLogs(env, runId);
      return json(request, env, { logs });
    }

    // Prompt APIs
    if (path === "/admin/api/prompt" && request.method === "GET") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      const settings = await getSettings(env, ["summarize_prompt"]);
      const custom = settings["summarize_prompt"];
      const effective = (custom && custom.trim().length > 0) ? custom : STRUCTURED_PROMPT;
      return json(request, env, { prompt: effective, custom });
    }
    if (path === "/admin/api/prompt" && request.method === "PUT") {
      if (!(await isAuthorized(request, env))) return corsResponse(request, env, 401);
      try {
        const { prompt } = await request.json();
        await upsertSetting(env, "summarize_prompt", String(prompt || ""));
        return json(request, env, { message: "Prompt updated" });
      } catch (e) {
        return json(request, env, { error: String(e) }, 400);
      }
    }

    return corsResponse(404);
  },

  async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext) {
    ctx.waitUntil(runOnce(env));
  },
};

async function runOnce(env: Env) {
  const run_id = crypto.randomUUID();
  const started_at = nowIso();
  await markRunStart(env, run_id);
  log({ lvl: "info", msg: "run start", run_id });
  await appendRunLog(env, run_id, "info", "run start");
  await appendRunLog(env, run_id, "info", "🚀 Starting AI Market Intelligence Analysis…");
  try {
    const settings = await getSettings(env, [
      "recipient_emails",
      "max_concurrency",
      "max_articles_considered",
      "max_articles_for_ai",
      "per_source_cap",
      "ai_primary",
      "gemini_model_id",
      "openai_model_id",
      "openai_reasoning",
      "watchlist",
      "summarize_prompt",
      "email_from",
    ]);
    const recipients: string[] = parseJsonArray(settings["recipient_emails"]) || [];
    const maxConcurrency = parseInt(settings["max_concurrency"] || "6", 10) || 6;
    const maxConsidered = parseInt(settings["max_articles_considered"] || "60", 10) || 60;
    const maxForAi = parseInt(settings["max_articles_for_ai"] || "25", 10) || 25;
    const watchlist: string[] = parseJsonArray(settings["watchlist"]) || ["SPY","QQQ","IWM","GLD","BTC","UUP"];
    const prompt = settings["summarize_prompt"] || undefined;
    const fromAddress = settings["email_from"] || (env as any).RESEND_FROM || "digest@yourdomain.com";

    // AI provider configuration summary
    const aiConfig = {
      primary: (settings["ai_primary"] || 'gemini'),
      gemini_model: settings["gemini_model_id"] || (env as any).GEMINI_MODEL_ID || 'gemini-2.5-flash',
      openai_model: settings["openai_model_id"] || (env as any).OPENAI_MODEL_ID || 'gpt-5-mini',
      openai_reasoning: settings["openai_reasoning"] || null,
      has_gemini_key: Boolean((env as any).GEMINI_API_KEY),
      has_openai_key: Boolean((env as any).OPENAI_API_KEY),
    };
    await appendRunLog(env, run_id, "info", "🤖 AI providers configured", aiConfig as any);
    if (String(aiConfig.primary).toLowerCase() === 'openai' && !aiConfig.has_openai_key) {
      await appendRunLog(env, run_id, "warn", "OpenAI selected as primary but OPENAI_API_KEY is missing");
    }
    if (String(aiConfig.primary).toLowerCase() === 'gemini' && !aiConfig.has_gemini_key) {
      await appendRunLog(env, run_id, "warn", "Gemini selected as primary but GEMINI_API_KEY is missing");
    }

    const feeds = await getEnabledFeeds(env);
    const feedUrls = feeds.map(f => f.url);
    await appendRunLog(env, run_id, "info", "📰 Fetching RSS feeds…", { feeds_total: feedUrls.length, max_concurrency: maxConcurrency });
    const fetched = await fetchFeeds(env, feedUrls, maxConcurrency);
    const feeds_ok = fetched.filter(f => f.ok).length;
    await appendRunLog(env, run_id, "info", "✅ RSS collection complete", { feeds_total: feedUrls.length, feeds_ok, failed: feedUrls.length - feeds_ok });
    // Per-feed logging
    for (const fr of fetched) {
      await appendRunLog(env, run_id, fr.ok ? "info" : "warn", "feed result", {
        feedUrl: fr.feedUrl,
        ok: fr.ok,
        items: fr.items?.length || 0,
        error: fr.error || null
      });
    }

    const rawItems: RawItem[] = [];
    for (const f of fetched) if (f.ok) rawItems.push(...f.items.map(it => ({ title: it.title, link: it.link, published_at: it.published_at || null, description: it.description || null })));
    // Trim to consideration cap
    rawItems.splice(maxConsidered);

    const normalized = (await Promise.all(rawItems.map(normalizeAndHash))).filter(Boolean) as Awaited<ReturnType<typeof normalizeAndHash>>[];
    let newCount = 0;
    const freshArticles = [] as {
      title: string; url: string; source: string; published_at: string | null; content_hash: string; article_id?: number | null; description?: string | null;
    }[];

    for (const n of normalized) {
      if (await hasSeenHash(env, n.content_hash)) continue;
      await insertSeenHash(env, n.content_hash);
      const articleId = await insertArticle(env, {
        content_hash: n.content_hash,
        source: n.source,
        title: n.title,
        canonical_url: n.canonical_url,
        published_at: n.published_at,
      });
      freshArticles.push({
        title: n.title,
        url: n.canonical_url,
        source: n.source,
        published_at: n.published_at,
        content_hash: n.content_hash,
        description: n.description || null,
        article_id: articleId,
      });
      newCount++;
    }

    const perSourceCap = Math.max(1, Math.min(50, parseInt(settings["per_source_cap"] || "10", 10) || 10));
    const ranked = rankItems(freshArticles, watchlist, maxForAi, perSourceCap);
    await appendRunLog(env, run_id, "info", "articles ranked", { ranked: ranked.length });
    for (let i = 0; i < ranked.length; i++) {
      const ra = ranked[i];
      if (ra.item.article_id) await addRunArticle(env, run_id, ra.item.article_id, i + 1, ra.score);
    }

    // Fetch market data for watchlist symbols
    const marketData = await fetchMarketData(env, watchlist);
    await saveMarketData(env, run_id, marketData);

    // Summarize
    const summaryInput = ranked.map(r => ({ title: r.item.title, url: r.item.url, source: r.item.source, description: r.item.description || undefined }));
    const aiSettings = {
      ai_primary: settings["ai_primary"],
      gemini_model_id: settings["gemini_model_id"],
      openai_model_id: settings["openai_model_id"],
      openai_reasoning: settings["openai_reasoning"],
    };
    await appendRunLog(env, run_id, "info", "🤖 Attempting AI analysis", {
      primary: (aiSettings.ai_primary || 'gemini'),
      gemini_model: aiSettings.gemini_model_id || (env as any).GEMINI_MODEL_ID || 'gemini-2.5-flash',
      openai_model: aiSettings.openai_model_id || (env as any).OPENAI_MODEL_ID || 'gpt-5-mini',
      reasoning: aiSettings.openai_reasoning || null
    });
    const summary = await summarizeWithAI(env, summaryInput, marketData, watchlist, aiSettings, prompt, run_id);
    const fallbackSummary = !summary.ok;
    const summaryHtml = summary.ok ? summary.html : fallbackHeadlines(summaryInput);
    if (!summary.ok) await appendRunLog(env, run_id, "warn", "ai summary failed", { error: summary.error });
    await appendRunLog(env, run_id, "info", "ai summary", { provider: summary.provider || null, tokens_in: summary.tokens_in || 0, tokens_out: summary.tokens_out || 0, ok: summary.ok });
    if (summary.ok && summary.provider) {
      const primary = (aiSettings.ai_primary || 'gemini').toLowerCase();
      const usedProvider = summary.provider.toLowerCase().includes('openai') ? 'openai' : (summary.provider.toLowerCase().includes('gemini') ? 'gemini' : summary.provider.toLowerCase());
      if (usedProvider !== primary) {
        await appendRunLog(env, run_id, "info", "🔁 Fallback provider used", { primary, used: usedProvider, provider_label: summary.provider });
      }
    }

    const subject = `Market Intel – ${new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "2-digit" })}`;
    await appendRunLog(env, run_id, "info", "📧 Preparing to send email", { recipients: recipients.length, from: fromAddress });
    const emailRes = recipients.length ? await sendDigestEmail(
      env,
      recipients,
      subject,
      summaryHtml,
      marketData,
      ranked.map(r => r.item),
      fromAddress,
      { feeds_ok, feeds_total: feedUrls.length, articles_seen: normalized.length, articles_used: ranked.length, ai_provider: summary.provider }
    ) : { ok: true } as any;
    if (!emailRes.ok) await appendRunLog(env, run_id, "error", "email send failed", { error: emailRes.error });
    else await appendRunLog(env, run_id, "info", "email sent", { recipients: recipients.length, subject });

    // Save digest
    await saveDigestHtml(env, run_id, summaryHtml);

    const status = (emailRes.ok && summary.ok) ? "success" : (feeds_ok > 0 ? "partial" : "failed");
    await markRunFinish(env, run_id, {
      status,
      feeds_total: feedUrls.length,
      feeds_ok,
      articles_seen: normalized.length,
      articles_used: ranked.length,
      ai_tokens_in: summary.tokens_in || 0,
      ai_tokens_out: summary.tokens_out || 0,
      email_sent: emailRes.ok ? 1 : 0,
    });

    const res = { status, run_id, feeds_total: feedUrls.length, feeds_ok, new_articles: newCount, used: ranked.length, email_ok: emailRes.ok, started_at };
    log({ lvl: "info", msg: "run finish", ...res });
    await appendRunLog(env, run_id, "info", "run finish", res as any);
    return res;
  } catch (e: any) {
    await markRunFinish(env, run_id, { status: "failed" });
    log({ lvl: "error", msg: "run failed", run_id, error: String(e) });
    await appendRunLog(env, run_id, "error", "run failed", { error: String(e) });
    return { status: "failed", run_id, error: String(e), started_at };
  }
}

function fallbackHeadlines(items: { title: string; url: string; source: string }[]): string {
  const bullets = items.slice(0, 12).map(it => `<li><b>${escape(it.title)}</b> – <a href="${escape(it.url)}" target="_blank" rel="noopener noreferrer">${escape(it.source)}</a></li>`).join("");
  return `<h3>What changed today</h3><ul>${bullets}</ul>`;
}

function escape(s: string): string { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

function json(request: Request, env: Env, obj: any, status = 200): Response {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...jsonHeaders(request, env) }
  });
}

function corsResponse(request: Request, env: Env, status = 200): Response {
  return new Response(null, {
    status,
    headers: { ...jsonHeaders(request, env) }
  });
}

function jsonHeaders(request: Request, env: Env): Record<string, string> {
  const origin = request.headers.get("Origin") || "*";
  const allowCreds = "true";
  const allowed = allowedOrigin(origin, env) || (env.DEV_MODE === "1" ? origin : "");
  const headers: Record<string, string> = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Cf-Access-Authenticated-User-Email",
    "Vary": "Origin",
  };
  if (allowed) {
    headers["Access-Control-Allow-Origin"] = allowed;
    headers["Access-Control-Allow-Credentials"] = allowCreds;
  } else {
    headers["Access-Control-Allow-Origin"] = "*";
    headers["Access-Control-Allow-Credentials"] = "false";
  }
  return headers;
}

function htmlHeaders(request: Request, env: Env): Record<string, string> {
  const origin = request.headers.get("Origin") || "*";
  const allowed = allowedOrigin(origin, env) || (env.DEV_MODE === "1" ? origin : "");
  const headers: Record<string, string> = {
    "Content-Type": "text/html; charset=utf-8",
    "Vary": "Origin",
  };
  if (allowed) {
    headers["Access-Control-Allow-Origin"] = allowed;
    headers["Access-Control-Allow-Credentials"] = "true";
  }
  return headers;
}

function allowedOrigin(origin: string, env: Env): string | null {
  try {
    const u = new URL(origin);
    const host = u.host;
    // Allow Pages subdomains for admin UI
    if (host.endsWith(".ai-market-intel-admin.pages.dev")) return `${u.protocol}//${u.host}`;
    // Allow explicit ALLOWED_ORIGIN if set
    const cfg = (env as any).ALLOWED_ORIGIN;
    if (cfg && (cfg === origin || cfg === `${u.protocol}//${u.host}`)) return `${u.protocol}//${u.host}`;
  } catch {}
  return null;
}

async function isAuthorized(request: Request, env: Env): Promise<boolean> {
  if (env.DEV_MODE === "1") return true;
  // Cloudflare Access authentication header
  const email = request.headers.get("Cf-Access-Authenticated-User-Email");
  if (email) return true;
  // Fallback: allow requests from explicitly allowed origin if configured
  const origin = request.headers.get("Origin") || "";
  const allowed = allowedOrigin(origin, env);
  if (allowed) return true;
  console.log("Authorization failed - missing Cf-Access and untrusted origin:", origin);
  return false;
}
