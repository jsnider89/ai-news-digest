import { canonicalizeUrl, dateOnly, toIsoOrNull, normalizeTitle, sha256Hex } from "./util";

export interface RawItem {
  title: string;
  link: string;
  published_at?: string | null;
  description?: string | null;
}

export interface NormalizedItem {
  title: string;
  canonical_url: string;
  source: string; // hostname
  published_at: string | null; // RFC3339 full timestamp (if available)
  content_hash: string; // sha256
  description?: string | null;
}

export async function normalizeAndHash(item: RawItem): Promise<NormalizedItem | null> {
  const urlInfo = canonicalizeUrl(item.link);
  if (!urlInfo) return null;
  const titleClean = normalizeTitle(item.title || "");
  const dateFull = toIsoOrNull(item.published_at) ?? null;
  const dateDay = dateOnly(item.published_at) ?? null;
  const parts = [titleClean, urlInfo.url, dateDay ?? "", urlInfo.host];
  const content_hash = await sha256Hex(parts.join("|"));
  return {
    title: item.title,
    canonical_url: urlInfo.url,
    source: urlInfo.host,
    published_at: dateFull,
    content_hash,
    description: item.description || null,
  };
}
