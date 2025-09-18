export type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue };

export const nowIso = () => new Date().toISOString();

export function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function redactSecrets(s: string): string {
  // Redact any 20+ char alphanumerics (API keys, tokens)
  return s.replace(/[A-Za-z0-9_\-]{20,}/g, "[REDACTED]");
}

export function parseJsonArray(s: string | null): string[] | null {
  if (!s) return null;
  try {
    const parsed = JSON.parse(s);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function log(obj: Record<string, JsonValue>) {
  try {
    const json = JSON.stringify(obj);
    console.log(redactSecrets(json));
  } catch (e) {
    console.log("[log-err]", String(e));
  }
}

export async function sha256Hex(input: string): Promise<string> {
  const enc = new TextEncoder();
  const data = enc.encode(input);
  const hashBuf = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuf));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function canonicalizeUrl(rawUrl: string): { url: string; host: string } | null {
  try {
    const u = new URL(rawUrl);
    // Drop common tracking params
    const params = u.searchParams;
    [
      "utm_source",
      "utm_medium",
      "utm_campaign",
      "utm_term",
      "utm_content",
      "utm_name",
      "mc_cid",
      "mc_eid",
      "gclid",
      "igshid",
    ].forEach((k) => params.delete(k));
    u.search = params.toString();
    return { url: u.toString(), host: u.hostname.toLowerCase() };
  } catch {
    return null;
  }
}

export function normalizeTitle(t: string): string {
  return t.trim().toLowerCase().replace(/[\s\p{P}]+/gu, " ").trim();
}

export function dateOnly(isoOrRaw?: string | null): string | null {
  if (!isoOrRaw) return null;
  try {
    const d = new Date(isoOrRaw);
    if (isNaN(d.getTime())) return null;
    return d.toISOString().slice(0, 10);
  } catch {
    return null;
  }
}

export function toIsoOrNull(isoOrRaw?: string | null): string | null {
  if (!isoOrRaw) return null;
  try {
    const d = new Date(isoOrRaw);
    if (isNaN(d.getTime())) return null;
    return d.toISOString();
  } catch {
    return null;
  }
}

// US Market (NYSE) holiday/closed detection (basic rules; NY timezone)
export function isUsMarketClosedNY(date = new Date()): boolean {
  const tz = 'America/New_York';
  const ny = toNY(date);
  const weekday = ny.getUTCDay(); // using shifted date in NY offset
  if (weekday === 0 || weekday === 6) return true; // Sun or Sat
  return isUsMarketHolidayNY(ny);
}

export function isUsMarketHolidayNY(nyDate: Date): boolean {
  const y = nyDate.getUTCFullYear();
  const m = nyDate.getUTCMonth(); // 0-based
  const d = nyDate.getUTCDate();

  // Helper to compare YYYY-MM-DD in NY
  const same = (dt: Date) => dt.getUTCFullYear() === y && dt.getUTCMonth() === m && dt.getUTCDate() === d;

  // Observed helpers
  const observedFixed = (month: number, day: number): Date => {
    const dt = nyDateFromYMD(y, month, day);
    const wd = dt.getUTCDay();
    if (wd === 6) return nyDateFromYMD(y, month, day - 1); // Sat -> Friday
    if (wd === 0) return nyDateFromYMD(y, month, day + 1); // Sun -> Monday
    return dt;
  };

  // Fixed-date holidays (with observation)
  const newYears = observedFixed(0, 1); // Jan 1
  const juneteenth = observedFixed(5, 19); // Jun 19
  const independence = observedFixed(6, 4); // Jul 4
  const christmas = observedFixed(11, 25); // Dec 25
  if ([newYears, juneteenth, independence, christmas].some(same)) return true;

  // Nth/last weekday holidays
  const mlk = nthWeekdayOfMonth(y, 0, 1, 3); // 3rd Mon Jan
  const presidents = nthWeekdayOfMonth(y, 1, 1, 3); // 3rd Mon Feb
  const memorial = lastWeekdayOfMonth(y, 4, 1); // Last Mon May
  const labor = nthWeekdayOfMonth(y, 8, 1, 1); // 1st Mon Sep
  const thanksgiving = nthWeekdayOfMonth(y, 11, 4, 4); // 4th Thu Nov
  if ([mlk, presidents, memorial, labor, thanksgiving].some(same)) return true;

  // Note: Good Friday omitted for simplicity (movable holiday)
  return false;
}

function nthWeekdayOfMonth(year: number, month: number, weekday: number, n: number): Date {
  // weekday: 0=Sun..6=Sat; find nth occurrence in given month in NY time
  const first = nyDateFromYMD(year, month, 1);
  const firstWd = first.getUTCDay();
  const delta = (weekday - firstWd + 7) % 7;
  const day = 1 + delta + (n - 1) * 7;
  return nyDateFromYMD(year, month, day);
}

function lastWeekdayOfMonth(year: number, month: number, weekday: number): Date {
  const last = nyDateFromYMD(year, month + 1, 0); // day 0 of next month = last day of month
  const lastWd = last.getUTCDay();
  const delta = (lastWd - weekday + 7) % 7;
  const day = last.getUTCDate() - delta;
  return nyDateFromYMD(year, month, day);
}

function nyDateFromYMD(year: number, month: number, day: number): Date {
  // Construct a Date corresponding to NY midnight UTC shift for that date
  const s = toNY(new Date(Date.UTC(year, month, day, 12, 0, 0))); // midday UTC to avoid DST edge
  // Return a Date object representing that same NY calendar date at 00:00 NY as a UTC timestamp
  const nyY = s.getUTCFullYear();
  const nyM = s.getUTCMonth();
  const nyD = s.getUTCDate();
  return toNY(new Date(Date.UTC(nyY, nyM, nyD, 0, 0, 0)));
}

function toNY(d: Date): Date {
  // Shift date to reflect NY calendar day by formatting and re-parsing
  const fmt = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const parts = fmt.formatToParts(d);
  const get = (t: string) => Number(parts.find(p => p.type === t)?.value);
  const y = get('year'), m = get('month') - 1, day = get('day'), h = get('hour'), min = get('minute'), s = get('second');
  return new Date(Date.UTC(y, m, day, h, min, s));
}

// Simple bounded concurrency (p-limit style)
export function pLimit(concurrency: number) {
  let active = 0;
  const queue: (() => void)[] = [];
  const next = () => {
    active--;
    const fn = queue.shift();
    if (fn) fn();
  };
  return async function <T>(fn: () => Promise<T>): Promise<T> {
    if (active >= concurrency) {
      await new Promise<void>((resolve) => queue.push(resolve));
    }
    active++;
    try {
      const res = await fn();
      next();
      return res;
    } catch (e) {
      next();
      throw e;
    }
  };
}

export async function withTimeout<T>(p: Promise<T>, ms: number, message = "timeout"): Promise<T> {
  let timer: number | undefined;
  const timeoutPromise = new Promise<never>((_, reject) => {
    // @ts-ignore - setTimeout in Workers returns number
    timer = setTimeout(() => reject(new Error(message)), ms);
  });
  try {
    // Race
    return await Promise.race([p, timeoutPromise]);
  } finally {
    // @ts-ignore
    if (timer) clearTimeout(timer);
  }
}

export type CircuitState = { failures: number; paused_until?: number };

export async function getCircuit(env: Env, key: string): Promise<CircuitState> {
  const raw = await env.MARKET_FLAGS.get(`cb:${key}`);
  if (!raw) return { failures: 0 };
  try { return JSON.parse(raw) as CircuitState; } catch { return { failures: 0 }; }
}

export async function setCircuit(env: Env, key: string, value: CircuitState, ttlSeconds: number) {
  await env.MARKET_FLAGS.put(`cb:${key}`, JSON.stringify(value), { expirationTtl: ttlSeconds });
}

export interface Env {
  DB: D1Database;
  MARKET_FLAGS: KVNamespace;
  RESEND_API_KEY: string;
  GEMINI_API_KEY: string;
  DEV_MODE?: string;
}
