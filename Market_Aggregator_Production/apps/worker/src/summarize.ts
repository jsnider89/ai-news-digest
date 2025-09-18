import { log, isUsMarketClosedNY } from "./util";
import type { Env } from "./util";
import type { MarketQuote } from "./market-data";
import { appendRunLog } from "./storage";

type AiSettings = {
  ai_primary?: string | null; // 'gemini' | 'openai'
  gemini_model_id?: string | null;
  openai_model_id?: string | null;
  openai_reasoning?: string | null; // optional hint
};

export interface SummaryInputItem {
  title: string;
  url: string;
  source: string;
  description?: string;
}

export interface SummarizeResult {
  ok: boolean;
  html: string; // safe HTML snippet to inject
  tokens_in?: number;
  tokens_out?: number;
  provider?: string;
  error?: string;
}

export const STRUCTURED_PROMPT = `You are a professional financial analyst creating a comprehensive market intelligence report.

Generate a structured report with exactly these sections:

## SECTION 1 - MARKET PERFORMANCE
[Market data will be injected here - you analyze the implications]
Provide a 3-4 sentence overarching market summary explaining what the price movements mean.

## SECTION 2 - TOP MARKET & ECONOMY STORIES (5 stories)
Select the 5 most important financial/economic stories. For each:
**Story Title**: [Headline]
[Write 4-6 sentences explaining the story, its market implications, and context]
Sources: [List relevant source URLs]

## SECTION 3 - GENERAL NEWS STORIES (10 stories)
Select 10 other significant news stories. For each:
**Story Title**: [Headline]
[Write 2-3 sentences summarizing the story and any broader implications]
Sources: [List relevant source URLs]

IMPORTANT:
- Use specific company names, tickers, and numbers when available
- Focus on market impact and investor implications
- Each story must cite actual sources from the provided articles
- Write in professional, analytical tone

### LOOKING AHEAD (Tomorrow)
Based on today's themes and scheduled events in sources, list concrete upcoming events for tomorrow and key themes to watch. Include times if mentioned.
`;

export async function summarizeWithGemini(
  env: Env,
  items: SummaryInputItem[],
  marketData: MarketQuote[],
  watchlist: string[],
  promptOverride?: string
): Promise<SummarizeResult> {
  if (!env.GEMINI_API_KEY) return { ok: false, html: "", error: "missing GEMINI_API_KEY" };
  const inputs = items.map((it, i) => `${i + 1}. ${it.title} [${it.url}]`).join("\n");
  // Group items by source and include short description snippets for context
  const bySource = new Map<string, SummaryInputItem[]>();
  for (const it of items) {
    const arr = bySource.get(it.source) || [];
    arr.push(it);
    bySource.set(it.source, arr);
  }
  const sourceBlocks: string[] = [];
  for (const [src, arr] of bySource) {
    sourceBlocks.push(`Source: ${src}`);
    for (const a of arr) {
      const snippet = (a.description || "").replace(/\s+/g, ' ').slice(0, 220);
      if (snippet) {
        sourceBlocks.push(`- ${a.title} — ${snippet}`);
      } else {
        sourceBlocks.push(`- ${a.title}`);
      }
    }
    sourceBlocks.push("");
  }
  const contextualSources = sourceBlocks.join("\n");
  const wl = (watchlist || []).join(", ");
  const header = promptOverride && promptOverride.trim().length > 0 ? promptOverride : STRUCTURED_PROMPT;

  const marketLines = (marketData || []).map((m) => `- ${m.symbol}: ${m.price.toFixed(2)} (${m.change >= 0 ? "+" : ""}${m.change.toFixed(2)}, ${m.changePercent >= 0 ? "+" : ""}${m.changePercent.toFixed(2)}%)`).join("\n");
  const injectedMarket = marketLines ? `\nTracked tickers: ${wl}\nCurrent quotes:\n${marketLines}\n` : `\nTracked tickers: ${wl}\n`;

  // Market/day awareness
  const nyDateStr = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'long', month: 'long', day: '2-digit', year: 'numeric' }).format(new Date());
  const isClosed = isUsMarketClosedNY(new Date());
  const allUnchanged = (marketData || []).length > 0 && (marketData || []).every(m => Math.abs(m.change) < 1e-6 && Math.abs(m.changePercent) < 1e-6);
  const statusNote = isClosed
    ? 'Market status: CLOSED (Weekend). Avoid repeating intraday tick moves. Provide a brief weekly recap or "since last close" overview and highlight upcoming events.'
    : (allUnchanged ? 'Market status: QUIET/UNCHANGED (likely closed). Focus on weekly recap and outlook; do not repeat unchanged tick data.' : '');

  const userText = `${header}\nToday (New York): ${nyDateStr}\n${statusNote ? statusNote + '\n' : ''}${injectedMarket}\nHeadlines (use as sources):\n${inputs}\n\nContext by source (snippets):\n${contextualSources}\n\nDo not use placeholder tokens like [Current Date] or [Today] — always write the actual date above.`;
  try {
    const model = (env as any).GEMINI_MODEL_ID || "gemini-2.5-flash";
    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=` + encodeURIComponent(env.GEMINI_API_KEY);
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: userText }]}],
        generationConfig: { temperature: 0.3, maxOutputTokens: 12000 },
      }),
    });
    if (!resp.ok) {
      const t = await resp.text();
      log({ lvl: "warn", msg: "gemini http error", status: resp.status, body: t.slice(0, 500) });
      // Try fallbacks
      const fb = await tryProviderFallbacks(env, userText);
      if (fb.ok) return fb;
      return { ok: false, html: "", error: `gemini status ${resp.status}` };
    }
    const data = await resp.json() as any;
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    const tokens_in = data?.usageMetadata?.promptTokenCount || 0;
    const tokens_out = data?.usageMetadata?.candidatesTokenCount || 0;
    const html = markdownToHtmlSafe(text);
    const provider = `Gemini ${model}`;
    return { ok: true, html, tokens_in, tokens_out, provider };
  } catch (e: any) {
    log({ lvl: "error", msg: "gemini call failed", error: String(e) });
    // Try fallbacks when Gemini throws
    try {
      const fb = await tryProviderFallbacks(env, userText);
      if (fb.ok) return fb;
    } catch {}
    return { ok: false, html: "", error: String(e) };
  }
}

export async function summarizeWithAI(
  env: Env,
  items: SummaryInputItem[],
  marketData: MarketQuote[],
  watchlist: string[],
  ai: AiSettings,
  promptOverride?: string,
  runId?: string
): Promise<SummarizeResult> {
  const primary = (ai.ai_primary || '').toLowerCase();
  if (primary === 'openai') {
    const r = await tryOpenAIThenGemini(env, buildUserText(env, items, marketData, watchlist, promptOverride), ai, runId);
    if (r.ok) return r;
    // try anthropic as last resort
    const a = await tryAnthropic(env, buildUserText(env, items, marketData, watchlist, promptOverride), ai, runId);
    if (a.ok) return a;
    return r; // return the failure from earlier
  }
  // default gemini primary
  const g = await tryGemini(env, buildUserText(env, items, marketData, watchlist, promptOverride), ai, runId);
  if (g.ok) return g;
  const o = await tryOpenAI(env, buildUserText(env, items, marketData, watchlist, promptOverride), ai, runId);
  if (o.ok) return o;
  const a = await tryAnthropic(env, buildUserText(env, items, marketData, watchlist, promptOverride), ai, runId);
  if (a.ok) return a;
  return { ok: false, html: "", error: `gemini: ${g.error || 'failed'}; openai: ${o.error || 'failed'}; anthropic: ${a.error || 'failed'}` };
}

function buildUserText(env: Env, items: SummaryInputItem[], marketData: MarketQuote[], watchlist: string[], promptOverride?: string) {
  const inputs = items.map((it, i) => `${i + 1}. ${it.title} [${it.url}]`).join("\n");
  const wl = (watchlist || []).join(", ");
  const header = promptOverride && promptOverride.trim().length > 0 ? promptOverride : STRUCTURED_PROMPT;
  const marketLines = (marketData || []).map((m) => `- ${m.symbol}: ${m.price.toFixed(2)} (${m.change >= 0 ? "+" : ""}${m.change.toFixed(2)}, ${m.changePercent >= 0 ? "+" : ""}${m.changePercent.toFixed(2)}%)`).join("\n");
  const injectedMarket = marketLines ? `\nTracked tickers: ${wl}\nCurrent quotes:\n${marketLines}\n` : `\nTracked tickers: ${wl}\n`;
  const nyDateStr = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'long', month: 'long', day: '2-digit', year: 'numeric' }).format(new Date());
  const isClosed = isUsMarketClosedNY(new Date());
  const allUnchanged = (marketData || []).length > 0 && (marketData || []).every(m => Math.abs(m.change) < 1e-6 && Math.abs(m.changePercent) < 1e-6);
  const statusNote = isClosed
    ? 'Market status: CLOSED (Weekend/Holiday). Avoid repeating intraday tick moves. Provide a brief weekly recap or "since last close" overview and highlight upcoming events.'
    : (allUnchanged ? 'Market status: QUIET/UNCHANGED (likely closed). Focus on weekly recap and outlook; do not repeat unchanged tick data.' : '');

  // Group by source context (descriptions)
  const bySource = new Map<string, SummaryInputItem[]>();
  for (const it of items) { const arr = bySource.get(it.source) || []; arr.push(it); bySource.set(it.source, arr);} 
  const sourceBlocks: string[] = [];
  for (const [src, arr] of bySource) {
    sourceBlocks.push(`Source: ${src}`);
    for (const a of arr) {
      const snippet = (a.description || "").replace(/\s+/g, ' ').slice(0, 220);
      sourceBlocks.push(`- ${a.title}${snippet ? ' — ' + snippet : ''}`);
    }
    sourceBlocks.push("");
  }
  const contextualSources = sourceBlocks.join("\n");

  return `${header}\nToday (New York): ${nyDateStr}\n${statusNote ? statusNote + '\n' : ''}${injectedMarket}\nHeadlines (use as sources):\n${inputs}\n\nContext by source (snippets):\n${contextualSources}\n\nDo not use placeholder tokens like [Current Date] or [Today] — always write the actual date above.`;
}

async function tryGemini(env: Env, userText: string, ai: AiSettings, runId?: string): Promise<SummarizeResult> {
  if (!env.GEMINI_API_KEY) return { ok: false, html: "", error: "missing GEMINI_API_KEY" };
  const model = (ai.gemini_model_id || (env as any).GEMINI_MODEL_ID || "gemini-2.5-flash");
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=` + encodeURIComponent(env.GEMINI_API_KEY);
  try {
    if (runId) {
      log({ lvl: "info", msg: "ai.invoke", provider: "gemini", model, path: "gemini.generateContent", run_id: runId });
      await safeAppend(env, runId, "info", "ai.invoke", { provider: "gemini", model, path: "gemini.generateContent" });
    }
    const resp = await fetchWithBackoff(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: userText }]}], generationConfig: { temperature: 0.3, maxOutputTokens: 12000 } }),
    });
    if (!resp.ok) {
      const t = await resp.text();
      const snippet = t.slice(0, 500);
      log({ lvl: "warn", msg: "ai.failed", provider: "gemini", model, status: resp.status, body: snippet, run_id: runId || null });
      if (runId) await safeAppend(env, runId, "warn", "ai.failed", { provider: "gemini", model, path: "gemini.generateContent", status: resp.status, body: snippet });
      return { ok: false, html: "", error: `gemini status ${resp.status}` };
    }
    const data = await resp.json() as any;
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    const tokens_in = data?.usageMetadata?.promptTokenCount || 0;
    const tokens_out = data?.usageMetadata?.candidatesTokenCount || 0;
    if (runId) {
      log({ lvl: "info", msg: "ai.result", provider: "gemini", model, ok: true, tokens_in, tokens_out, run_id: runId });
      await safeAppend(env, runId, "info", "ai.result", { provider: "gemini", model, tokens_in, tokens_out, ok: true });
    }
    return { ok: true, html: markdownToHtmlSafe(text), tokens_in, tokens_out, provider: `Gemini ${model}` };
  } catch (e: any) {
    log({ lvl: "error", msg: "ai.failed", provider: "gemini", model, error: String(e), run_id: runId || null });
    if (runId) await safeAppend(env, runId, "warn", "ai.failed", { provider: "gemini", model, error: String(e) });
    return { ok: false, html: "", error: String(e) };
  }
}

async function tryOpenAI(env: Env, userText: string, ai: AiSettings, runId?: string): Promise<SummarizeResult> {
  const openaiKey = (env as any).OPENAI_API_KEY;
  if (!openaiKey) return { ok: false, html: "", error: "missing OPENAI_API_KEY" };
  const model = ai.openai_model_id || (env as any).OPENAI_MODEL_ID || "gpt-5-mini";
  const useResponses = shouldUseResponses(model);
  try {
    if (runId) {
      log({ lvl: "info", msg: "ai.invoke", provider: "openai", model, path: useResponses ? "responses" : "chat.completions", run_id: runId });
      await safeAppend(env, runId, "info", "ai.invoke", { provider: "openai", model, path: useResponses ? "responses" : "chat.completions" });
    }
    let resp: Response;
    if (useResponses) {
      const body: any = {
        model,
        input: userText,
        instructions: `You are a professional financial analyst.${ai.openai_reasoning ? ` Reasoning effort: ${ai.openai_reasoning}.` : ''} Use clear headings and markdown formatting.`,
        max_output_tokens: 12000,
      };
      if (ai.openai_reasoning) (body as any).reasoning = { effort: ai.openai_reasoning };
      resp = await fetchWithBackoff("https://api.openai.com/v1/responses", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${openaiKey}` },
        body: JSON.stringify(body)
      });
      if (!resp.ok) {
        const t = await resp.text();
        const snippet = t.slice(0, 500);
        if (runId) {
          log({ lvl: "warn", msg: "ai.failed", provider: "openai", model, path: "responses", status: resp.status, body: snippet, run_id: runId });
          await safeAppend(env, runId, "warn", "ai.failed", { provider: "openai", model, path: "responses", status: resp.status, body: snippet });
        }
        return { ok: false, html: "", error: `openai responses status ${resp.status}` };
      }
      const data = await resp.json() as any;
      const text = (data?.output_text as string) || extractResponsesText(data);
      const tokens_in = (data?.usage?.input_tokens as number) || 0;
      const tokens_out = (data?.usage?.output_tokens as number) || 0;
      if (text && text.trim().length) {
        if (runId) {
          log({ lvl: "info", msg: "ai.result", provider: "openai", model, path: "responses", ok: true, tokens_in, tokens_out, run_id: runId });
          await safeAppend(env, runId, "info", "ai.result", { provider: "openai", model, path: "responses", tokens_in, tokens_out, ok: true });
        }
        return { ok: true, html: markdownToHtmlSafe(text), provider: `OpenAI ${model}`, tokens_in, tokens_out };
      }
      const snippet = JSON.stringify(data).slice(0, 500);
      if (runId) await safeAppend(env, runId, "warn", "ai.failed", { provider: "openai", model, path: "responses", reason: "empty_content", data: snippet });
      return { ok: false, html: "", error: "openai responses returned empty content" };
    } else {
      resp = await fetchWithBackoff("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${openaiKey}` },
        body: JSON.stringify({
          model,
          messages: [
            { role: "system", content: `You are a professional financial analyst.${ai.openai_reasoning ? ` Reasoning effort: ${ai.openai_reasoning}.` : ''} Use clear headings and markdown formatting.` },
            { role: "user", content: userText }
          ],
          temperature: 0.3,
          max_tokens: 12000
        })
      });
      if (!resp.ok) {
        const t = await resp.text();
        const snippet = t.slice(0, 500);
        if (runId) {
          log({ lvl: "warn", msg: "ai.failed", provider: "openai", model, path: "chat.completions", status: resp.status, body: snippet, run_id: runId });
          await safeAppend(env, runId, "warn", "ai.failed", { provider: "openai", model, path: "chat.completions", status: resp.status, body: snippet });
        }
        return { ok: false, html: "", error: `openai status ${resp.status}` };
      }
      const data = await resp.json() as any;
      const text = data?.choices?.[0]?.message?.content || "";
      const tokens_in = data?.usage?.prompt_tokens || 0;
      const tokens_out = data?.usage?.completion_tokens || 0;
      if (text && text.trim().length) {
        if (runId) {
          log({ lvl: "info", msg: "ai.result", provider: "openai", model, path: "chat.completions", ok: true, tokens_in, tokens_out, run_id: runId });
          await safeAppend(env, runId, "info", "ai.result", { provider: "openai", model, path: "chat.completions", tokens_in, tokens_out, ok: true });
        }
        return { ok: true, html: markdownToHtmlSafe(text), provider: `OpenAI ${model}`, tokens_in, tokens_out };
      }
      const snippet = JSON.stringify(data).slice(0, 500);
      if (runId) await safeAppend(env, runId, "warn", "ai.failed", { provider: "openai", model, path: "chat.completions", reason: "empty_content", data: snippet });
      return { ok: false, html: "", error: "openai returned empty content" };
    }
  } catch (e: any) {
    log({ lvl: "warn", msg: "ai.failed", provider: "openai", model, error: String(e), run_id: runId || null });
    if (runId) await safeAppend(env, runId, "warn", "ai.failed", { provider: "openai", model, error: String(e) });
    return { ok: false, html: "", error: String(e) };
  }
}

async function tryOpenAIThenGemini(env: Env, userText: string, ai: AiSettings, runId?: string): Promise<SummarizeResult> {
  const o = await tryOpenAI(env, userText, ai, runId);
  if (o.ok) return o;
  const g = await tryGemini(env, userText, ai, runId);
  if (g.ok) return g;
  return { ok: false, html: "", error: `openai: ${o.error || 'failed'}; gemini: ${g.error || 'failed'}` };
}

async function tryAnthropic(env: Env, userText: string, _ai: AiSettings, runId?: string): Promise<SummarizeResult> {
  const anthropicKey = (env as any).ANTHROPIC_API_KEY;
  if (!anthropicKey) return { ok: false, html: "" };
  try {
    const model = (env as any).ANTHROPIC_MODEL_ID || "claude-3-5-sonnet-20240620";
    if (runId) {
      log({ lvl: "info", msg: "ai.invoke", provider: "anthropic", model, path: "messages", run_id: runId });
      await safeAppend(env, runId, "info", "ai.invoke", { provider: "anthropic", model, path: "messages" });
    }
    const resp = await fetchWithBackoff("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "content-type": "application/json", "x-api-key": anthropicKey, "anthropic-version": "2023-06-01" },
      body: JSON.stringify({ model, max_tokens: 12000, messages: [{ role: "user", content: userText }] })
    });
    if (!resp.ok) {
      const t = await resp.text();
      const snippet = t.slice(0, 500);
      if (runId) {
        log({ lvl: "warn", msg: "ai.failed", provider: "anthropic", model, status: resp.status, body: snippet, run_id: runId });
        await safeAppend(env, runId, "warn", "ai.failed", { provider: "anthropic", model, status: resp.status, body: snippet });
      }
      return { ok: false, html: "", error: `anthropic status ${resp.status}` };
    }
    const data = await resp.json() as any;
    const text = data?.content?.[0]?.text || "";
    if (text && text.trim().length) {
      if (runId) {
        log({ lvl: "info", msg: "ai.result", provider: "anthropic", model, ok: true, run_id: runId });
        await safeAppend(env, runId, "info", "ai.result", { provider: "anthropic", model, ok: true });
      }
      return { ok: true, html: markdownToHtmlSafe(text), provider: `Anthropic ${model}` };
    }
    return { ok: false, html: "" };
  } catch (e: any) {
    log({ lvl: "warn", msg: "ai.failed", provider: "anthropic", error: String(e), run_id: runId || null });
    if (runId) await safeAppend(env, runId, "warn", "ai.failed", { provider: "anthropic", error: String(e) });
    return { ok: false, html: "", error: String(e) };
  }
}

async function fetchWithBackoff(input: RequestInfo, init: RequestInit, attempts = 3, baseDelay = 500): Promise<Response> {
  let lastErr: any = null;
  for (let i = 0; i < attempts; i++) {
    try {
      const resp = await fetch(input, init);
      if (resp.ok) return resp;
      if (resp.status >= 500 || resp.status === 429) {
        await delay(baseDelay * Math.pow(2, i));
        continue;
      }
      return resp;
    } catch (e) {
      lastErr = e;
      await delay(baseDelay * Math.pow(2, i));
    }
  }
  throw lastErr || new Error('fetch failed');
}

function delay(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

async function tryProviderFallbacks(env: Env, userText: string): Promise<SummarizeResult> {
  // Try OpenAI if configured
  const openaiKey = (env as any).OPENAI_API_KEY;
  if (openaiKey) {
    try {
      const model = (env as any).OPENAI_MODEL_ID || "gpt-4o-mini";
      const resp = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${openaiKey}` },
        body: JSON.stringify({
          model,
          messages: [
            { role: "system", content: "You are a professional financial analyst. Use clear headings and markdown formatting." },
            { role: "user", content: userText }
          ],
          temperature: 0.3,
          max_tokens: 12000
        })
      });
      if (resp.ok) {
        const data = await resp.json() as any;
        const text = data?.choices?.[0]?.message?.content || "";
        if (text && text.trim().length) return { ok: true, html: markdownToHtmlSafe(text), provider: `OpenAI ${model}` };
      }
    } catch (e) {
      log({ lvl: "warn", msg: "openai fallback failed", error: String(e) });
    }
  }
  // Try Anthropic if configured
  const anthropicKey = (env as any).ANTHROPIC_API_KEY;
  if (anthropicKey) {
    try {
      const model = (env as any).ANTHROPIC_MODEL_ID || "claude-3-5-sonnet-20240620";
      const resp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": anthropicKey,
          "anthropic-version": "2023-06-01"
        },
        body: JSON.stringify({ model, max_tokens: 12000, messages: [{ role: "user", content: userText }] })
      });
      if (resp.ok) {
        const data = await resp.json() as any;
        const text = data?.content?.[0]?.text || "";
        if (text && text.trim().length) return { ok: true, html: markdownToHtmlSafe(text), provider: `Anthropic ${model}` };
      }
    } catch (e) {
      log({ lvl: "warn", msg: "anthropic fallback failed", error: String(e) });
    }
  }
  return { ok: false, html: "" };
}

function shouldUseResponses(model: string): boolean {
  // Route newer models to the Responses API
  const m = model.toLowerCase();
  return m.startsWith("gpt-5") || m.startsWith("o3") || m.startsWith("o4");
}

function extractResponsesText(data: any): string {
  try {
    // 1) Prefer output_text if present
    if (typeof data?.output_text === 'string' && data.output_text.trim()) {
      return data.output_text as string;
    }
    // 2) Walk through the structured output array
    const out = Array.isArray(data?.output) ? data.output : [];
    const chunks: string[] = [];
    for (const item of out) {
      // Direct output_text type
      if (item?.type === 'output_text' && typeof item?.text === 'string' && item.text.trim()) {
        chunks.push(item.text);
        continue;
      }
      // Message container with content array
      const content = Array.isArray(item?.content) ? item.content : [];
      for (const c of content) {
        if (typeof c?.text === 'string' && c.text.trim()) {
          chunks.push(c.text);
        } else if (c?.type === 'output_text' && typeof c?.text === 'string' && c.text.trim()) {
          chunks.push(c.text);
        }
      }
    }
    if (chunks.length) return chunks.join("\n\n");
  } catch {}
  return "";
}

async function safeAppend(env: Env, runId: string, level: string, message: string, context?: any) {
  try {
    await appendRunLog(env, runId, level, message, context);
  } catch (_) {
    // ignore logging failures
  }
}

function markdownToHtmlSafe(md: string): string {
  // Minimal markdown to HTML: bullet lines and links
  const lines = md.split(/\r?\n/);
  const out: string[] = [];
  let inList = false;
  for (const line of lines) {
    // SECTION headings without markdown
    const sec = line.match(/^\s*SECTION\s+\d+\s*-\s+(.+)$/i);
    if (sec) {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<h2>${linkify(escapeHtmlLite(sec[1]))}</h2>`);
      continue;
    }
    const look = line.match(/^\s*LOOKING AHEAD.*$/i);
    if (look) {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<h2>${linkify(escapeHtmlLite(line.trim()))}</h2>`);
      continue;
    }
    // Headings ## or ###
    const h = line.match(/^\s*(#{2,3})\s+(.+)$/);
    if (h) {
      if (inList) { out.push("</ul>"); inList = false; }
      const level = h[1].length === 2 ? "h2" : "h3";
      out.push(`<${level}>${linkify(escapeHtmlLite(h[2]))}</${level}>`);
      continue;
    }
    // Numbered list "1. "
    const num = line.match(/^\s*\d+\.\s+(.*)$/);
    if (num) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${linkify(inlineEmphasis(escapeHtmlLite(num[1])))}</li>`);
      continue;
    }
    const m = line.match(/^\s*[-*]\s+(.*)$/);
    if (m) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${linkify(inlineEmphasis(escapeHtmlLite(m[1])))}</li>`);
    } else if (line.trim() === "") {
      if (inList) { out.push("</ul>"); inList = false; }
    } else {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<p>${linkify(inlineEmphasis(escapeHtmlLite(line)))}</p>`);
    }
  }
  if (inList) out.push("</ul>");
  return out.join("");
}

function escapeHtmlLite(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;").replace(/'/g, "&#39;");
}

function linkify(s: string): string {
  let out = s;
  // Markdown links [text](url)
  out = out.replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, (_m, text, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${escapeHtmlLite(text)}</a>`);
  // Bracket-lone URLs [https://...]
  out = out.replace(/\[(https?:[^\]]+)\]/g, (_m, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${escapeHtmlLite(url)}</a>`);
  // Bare URLs
  out = out.replace(/(^|\s)(https?:\/\/[^\s)]+)(?=$|\s)/g, (_m, pre, url) => `${pre}<a href="${url}" target="_blank" rel="noopener noreferrer">${escapeHtmlLite(url)}</a>`);
  return out;
}

function inlineEmphasis(s: string): string {
  // Bold **text** and italics *text*
  let out = s.replace(/\*\*([^*]+)\*\*/g, (_m, t) => `<strong>${t}</strong>`);
  out = out.replace(/\*([^*]+)\*/g, (_m, t) => `<em>${t}</em>`);
  return out;
}
