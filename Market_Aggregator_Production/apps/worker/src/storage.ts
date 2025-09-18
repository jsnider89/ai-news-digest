import { nowIso } from "./util";
import type { Env } from "./util";

export interface FeedRow {
  id: number;
  name: string;
  url: string;
  category: string | null;
  enabled: number;
}

export interface ArticleRow {
  id: number;
  content_hash: string;
  source: string;
  title: string;
  canonical_url: string;
  published_at: string | null;
}

export interface RunRow {
  run_id: string;
  started_at: string | null;
  finished_at: string | null;
  status: string | null;
  feeds_total: number | null;
  feeds_ok: number | null;
  articles_seen: number | null;
  articles_used: number | null;
  ai_tokens_in: number | null;
  ai_tokens_out: number | null;
  email_sent: number | null;
}

export interface RunLogRow {
  run_id: string;
  ts: string;
  level: string;
  message: string;
  context_json: string | null;
}

export interface MarketDataRow {
  run_id: string;
  symbol: string;
  price: number;
  change_amount: number;
  change_percent: number;
  timestamp?: string;
}

export async function getFeeds(env: Env): Promise<FeedRow[]> {
  const { results } = await env.DB.prepare(
    "SELECT id, name, url, category, enabled FROM feeds ORDER BY id"
  ).all<FeedRow>();
  return results ?? [];
}

export async function getEnabledFeeds(env: Env): Promise<FeedRow[]> {
  const { results } = await env.DB.prepare(
    "SELECT id, name, url, category, enabled FROM feeds WHERE enabled = 1 ORDER BY id"
  ).all<FeedRow>();
  return results ?? [];
}

export async function getSetting(env: Env, key: string): Promise<string | null> {
  const { results } = await env.DB.prepare(
    "SELECT value FROM settings WHERE key = ?"
  ).bind(key).all<{ value: string }>();
  return results && results[0] ? results[0].value : null;
}

export async function getSettings(env: Env, keys: string[]): Promise<Record<string, string | null>> {
  const map: Record<string, string | null> = {};
  for (const k of keys) map[k] = await getSetting(env, k);
  return map;
}

export async function upsertSetting(env: Env, key: string, value: string) {
  await env.DB.prepare(
    "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value"
  ).bind(key, value).run();
}

export async function markRunStart(env: Env, run_id: string) {
  await env.DB.prepare(
    `INSERT INTO runs(run_id, started_at, status) VALUES(?, ?, ?)`
  ).bind(run_id, nowIso(), "started").run();
}

export async function markRunFinish(env: Env, run_id: string, data: Partial<RunRow>) {
  const flds: string[] = ["finished_at = ?"]; const vals: any[] = [nowIso()];
  for (const [k, v] of Object.entries(data)) { flds.push(`${k} = ?`); vals.push(v); }
  vals.push(run_id);
  await env.DB.prepare(`UPDATE runs SET ${flds.join(", ")} WHERE run_id = ?`).bind(...vals).run();
}

export async function insertSeenHash(env: Env, content_hash: string) {
  await env.DB.prepare(
    "INSERT OR IGNORE INTO seen_hashes(content_hash) VALUES(?)"
  ).bind(content_hash).run();
}

export async function hasSeenHash(env: Env, content_hash: string): Promise<boolean> {
  const { results } = await env.DB.prepare(
    "SELECT content_hash FROM seen_hashes WHERE content_hash = ?"
  ).bind(content_hash).all<{ content_hash: string }>();
  return !!(results && results[0]);
}

export async function insertArticle(env: Env, a: Omit<ArticleRow, "id">): Promise<number | null> {
  const res = await env.DB.prepare(
    "INSERT OR IGNORE INTO articles(content_hash, source, title, canonical_url, published_at) VALUES(?, ?, ?, ?, ?)"
  ).bind(a.content_hash, a.source, a.title, a.canonical_url, a.published_at).run();
  if (res.success) {
    const { results } = await env.DB.prepare(
      "SELECT id FROM articles WHERE content_hash = ?"
    ).bind(a.content_hash).all<{ id: number }>();
    return results && results[0] ? results[0].id : null;
  }
  return null;
}

export async function addRunArticle(env: Env, run_id: string, article_id: number, rank: number, score: number) {
  await env.DB.prepare(
    "INSERT INTO run_articles(run_id, article_id, rank, score) VALUES(?, ?, ?, ?)"
  ).bind(run_id, article_id, rank, score).run();
}

export async function saveDigestHtml(env: Env, run_id: string, html: string) {
  await env.DB.prepare(
    "INSERT INTO digests(run_id, html) VALUES(?, ?) ON CONFLICT(run_id) DO UPDATE SET html = excluded.html"
  ).bind(run_id, html).run();
}

export async function getLatestRun(env: Env): Promise<RunRow | null> {
  const { results } = await env.DB.prepare(
    "SELECT * FROM runs ORDER BY started_at DESC LIMIT 1"
  ).all<RunRow>();
  return results && results[0] ? results[0] : null;
}

export async function getLatestDigestHtml(env: Env): Promise<string | null> {
  const { results } = await env.DB.prepare(
    `SELECT digests.html FROM digests JOIN runs ON digests.run_id = runs.run_id
     ORDER BY runs.started_at DESC LIMIT 1`
  ).all<{ html: string }>();
  return results && results[0] ? results[0].html : null;
}

export async function getDigestHtmlByRun(env: Env, run_id: string): Promise<string | null> {
  const { results } = await env.DB.prepare(
    `SELECT html FROM digests WHERE run_id = ?`
  ).bind(run_id).all<{ html: string }>();
  return results && results[0] ? results[0].html : null;
}

// Feed management
export async function addFeed(env: Env, feed: Omit<FeedRow, "id">): Promise<number> {
  const res = await env.DB.prepare(
    "INSERT INTO feeds(name, url, category, enabled) VALUES(?, ?, ?, ?)"
  ).bind(feed.name, feed.url, feed.category, feed.enabled).run();
  return res.meta.last_row_id as number;
}

export async function updateFeed(env: Env, id: number, feed: Partial<Omit<FeedRow, "id">>): Promise<void> {
  const fields: string[] = [];
  const values: any[] = [];
  
  if (feed.name !== undefined) { fields.push("name = ?"); values.push(feed.name); }
  if (feed.url !== undefined) { fields.push("url = ?"); values.push(feed.url); }
  if (feed.category !== undefined) { fields.push("category = ?"); values.push(feed.category); }
  if (feed.enabled !== undefined) { fields.push("enabled = ?"); values.push(feed.enabled); }
  
  if (fields.length === 0) return;
  
  values.push(id);
  await env.DB.prepare(`UPDATE feeds SET ${fields.join(", ")} WHERE id = ?`).bind(...values).run();
}

export async function deleteFeed(env: Env, id: number): Promise<void> {
  await env.DB.prepare("DELETE FROM feeds WHERE id = ?").bind(id).run();
}

// Runs listing and details
export async function getRuns(env: Env, limit = 50): Promise<RunRow[]> {
  const { results } = await env.DB.prepare(
    `SELECT * FROM runs ORDER BY started_at DESC LIMIT ?`
  ).bind(limit).all<RunRow>();
  return results ?? [];
}

export async function getRunById(env: Env, run_id: string): Promise<RunRow | null> {
  const { results } = await env.DB.prepare(
    `SELECT * FROM runs WHERE run_id = ?`
  ).bind(run_id).all<RunRow>();
  return results && results[0] ? results[0] : null;
}

// Run logs
export async function appendRunLog(env: Env, run_id: string, level: string, message: string, context?: any) {
  const ctx = context == null ? null : JSON.stringify(context).slice(0, 4000);
  await env.DB.prepare(
    `INSERT INTO run_logs(run_id, ts, level, message, context_json) VALUES(?, ?, ?, ?, ?)`
  ).bind(run_id, nowIso(), level, message, ctx).run();
}

export async function getRunLogs(env: Env, run_id: string): Promise<RunLogRow[]> {
  const { results } = await env.DB.prepare(
    `SELECT run_id, ts, level, message, context_json FROM run_logs WHERE run_id = ? ORDER BY ts`
  ).bind(run_id).all<RunLogRow>();
  return results ?? [];
}

// Admin utility: delete seen hashes in the last N hours
export async function resetSeenHashesHours(env: Env, hours: number): Promise<number> {
  const interval = `-${Math.max(1, Math.min(168, Math.floor(hours)))} hours`;
  const res = await env.DB.prepare(
    `DELETE FROM seen_hashes WHERE first_seen_at >= datetime('now', ?)`
  ).bind(interval).run();
  // D1 returns meta.changes
  // @ts-ignore
  return (res?.meta?.changes as number) ?? 0;
}

export async function countSeenHashesSince(env: Env, hours: number): Promise<number> {
  const interval = `-${Math.max(1, Math.min(168, Math.floor(hours)))} hours`;
  const { results } = await env.DB.prepare(
    `SELECT COUNT(*) as cnt FROM seen_hashes WHERE first_seen_at >= datetime('now', ?)`
  ).bind(interval).all<{ cnt: number }>();
  return results && results[0] ? (results[0].cnt as unknown as number) : 0;
}

// Market data persistence
export async function saveMarketData(env: Env, run_id: string, marketData: { symbol: string; price: number; change: number; changePercent: number; }[]) {
  if (!marketData || marketData.length === 0) return;
  const stmt = env.DB.prepare(
    `INSERT INTO market_data(run_id, symbol, price, change_amount, change_percent) VALUES(?, ?, ?, ?, ?)
     ON CONFLICT(run_id, symbol) DO UPDATE SET price = excluded.price, change_amount = excluded.change_amount, change_percent = excluded.change_percent`
  );
  for (const m of marketData) {
    await stmt.bind(run_id, m.symbol, m.price, m.change, m.changePercent).run();
  }
}

export async function getMarketDataByRun(env: Env, run_id: string): Promise<MarketDataRow[]> {
  const { results } = await env.DB.prepare(
    `SELECT run_id, symbol, price, change_amount, change_percent, timestamp FROM market_data WHERE run_id = ? ORDER BY symbol`
  ).bind(run_id).all<MarketDataRow>();
  return results ?? [];
}
