import type { Env } from "./util";

export interface MarketQuote {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
}

// Fetch market quotes for the provided symbols using Finnhub's quote API
// https://finnhub.io/docs/api/quote
export async function fetchMarketData(env: Env, symbols: string[]): Promise<MarketQuote[]> {
  const token = (env as any).FINNHUB_API_KEY || (env as any).FINNHUB_TOKEN || "";
  if (!token || symbols.length === 0) return [];

  const unique = Array.from(new Set(symbols.map((s) => String(s || "").toUpperCase()).filter(Boolean)));
  const results: MarketQuote[] = [];

  // Finnhub has per-second limits on free tier; fetch sequentially to be safe
  for (const sym of unique) {
    try {
      const url = `https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(sym)}&token=${encodeURIComponent(token)}`;
      const resp = await fetch(url, { method: "GET" });
      if (!resp.ok) continue;
      const data = await resp.json() as any;
      const price = Number(data?.c ?? NaN);
      const change = Number(data?.d ?? NaN);
      const changePercent = Number(data?.dp ?? NaN);
      if (Number.isFinite(price) && Number.isFinite(change) && Number.isFinite(changePercent)) {
        results.push({ symbol: sym, price, change, changePercent });
      }
    } catch {
      // ignore one-off failures; continue with others
    }
  }
  return results;
}

