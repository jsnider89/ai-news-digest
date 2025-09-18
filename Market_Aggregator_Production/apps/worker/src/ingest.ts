import { pLimit, withTimeout, log } from "./util";
import { XMLParser } from "fast-xml-parser";
import type { Env } from "./util";

export interface FeedResultItem {
  title: string;
  link: string;
  published_at?: string | null;
  description?: string | null;
}

export interface FeedFetchResult {
  feedUrl: string;
  ok: boolean;
  items: FeedResultItem[];
  error?: string;
}

export async function fetchFeeds(env: Env, feedUrls: string[], maxConcurrency = 6, timeoutMs = 10000): Promise<FeedFetchResult[]> {
  const limit = pLimit(maxConcurrency);
  const tasks = feedUrls.map((url) => limit(async () => fetchOne(url, timeoutMs)));
  const settled = await Promise.allSettled(tasks);
  return settled.map((res, i) => {
    if (res.status === "fulfilled") return res.value;
    return { feedUrl: feedUrls[i], ok: false, items: [], error: String(res.reason) };
  });
}

async function fetchOne(feedUrl: string, timeoutMs: number): Promise<FeedFetchResult> {
  try {
    const res = await withTimeout(fetch(feedUrl, { headers: { "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9" } }), timeoutMs);
    if (!res.ok) return { feedUrl, ok: false, items: [], error: `status ${res.status}` };
    const text = await res.text();
    const items = parseFeed(text);
    return { feedUrl, ok: true, items };
  } catch (e: any) {
    log({ lvl: "warn", msg: "feed fetch error", feedUrl, error: String(e) });
    return { feedUrl, ok: false, items: [], error: String(e) };
  }
}

// Robust RSS/Atom parser using fast-xml-parser (works in Workers)
export function parseFeed(xml: string): FeedResultItem[] {
  try {
    const parser = new XMLParser({ ignoreAttributes: false, attributeNamePrefix: "@_", trimValues: true });
    const doc = parser.parse(xml);
    const out: FeedResultItem[] = [];
    // RSS 2.0
    const rssItems = doc?.rss?.channel?.item;
    if (rssItems && Array.isArray(rssItems)) {
      for (const it of rssItems) {
        const title = it?.title?.toString() || "";
        const link = it?.link?.toString() || (it?.guid?.toString() || "");
        const pub = it?.pubDate?.toString() || it?.published?.toString() || null;
        const desc = (it?.description?.toString() || it?.summary?.toString() || null);
        if (title && link) out.push({ title, link, published_at: pub, description: desc });
      }
      return out;
    }
    // Atom
    const entries = doc?.feed?.entry;
    if (entries && Array.isArray(entries)) {
      for (const en of entries) {
        const title = en?.title?.toString() || "";
        let link = "";
        if (en?.link) {
          if (Array.isArray(en.link)) {
            const alt = en.link.find((l: any) => (l?.['@_rel'] || 'alternate') === 'alternate' && l?.['@_href']);
            link = alt?.['@_href'] || en.link[0]?.['@_href'] || "";
          } else {
            link = en.link?.['@_href'] || en.link?.toString() || "";
          }
        }
        const pub = en?.updated?.toString() || en?.published?.toString() || null;
        const desc = (en?.summary?.toString() || en?.content?.toString() || null);
        if (title && link) out.push({ title, link, published_at: pub, description: desc });
      }
      return out;
    }
    return out;
  } catch (e) {
    log({ lvl: "warn", msg: "xml parse failed", error: String(e) });
    return [];
  }
}
