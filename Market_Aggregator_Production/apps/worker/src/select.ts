export interface ScoredItem<T> { item: T; score: number }

// Simple topic-aware ranking: recency + cluster boost (similar titles within last ~12h)
export function rankItems<T extends { title: string; published_at: string | null; source?: string }>(
  items: T[],
  _watchlist: string[] = [],
  limit = 25,
  perSourceCap = 10
): ScoredItem<T>[] {
  const now = Date.now();
  const tokens = items.map((it) => tokenizeTitle(it.title));

  // Pairwise Jaccard similarity to form topic clusters
  const n = items.length;
  const parent = Array.from({ length: n }, (_, i) => i);
  const find = (x: number): number => (parent[x] === x ? x : (parent[x] = find(parent[x])));
  const unite = (a: number, b: number) => { const ra = find(a), rb = find(b); if (ra !== rb) parent[rb] = ra; };

  const simThreshold = 0.4;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const s = jaccard(tokens[i], tokens[j]);
      if (s >= simThreshold) unite(i, j);
    }
  }
  const clusterSize = new Array<number>(n).fill(0);
  for (let i = 0; i < n; i++) clusterSize[find(i)]++;

  const scored: ScoredItem<T>[] = items.map((it, idx) => {
    let score = 0;
    if (it.published_at) {
      const t = Date.parse(it.published_at);
      if (!isNaN(t)) {
        const hours = (now - t) / (1000 * 60 * 60);
        // Heavier weight for <= 12h window; then taper to 24h
        if (hours <= 12) score += (12 - hours) * 2; // up to 24 points
        score += Math.max(0, 24 - hours);          // up to 24 points
      }
    }
    const csz = clusterSize[find(idx)] || 1;
    // Topic boost: reward items in larger clusters (distinct sources likely)
    score += Math.max(0, csz - 1) * 6; // +6 per additional article on the same topic
    return { item: it, score };
  });
  scored.sort((a, b) => b.score - a.score);

  // Enforce simple source diversity cap
  const selected: ScoredItem<T>[] = [];
  const counts = new Map<string, number>();
  for (const s of scored) {
    if (selected.length >= limit) break;
    const src = (s.item as any).source || "";
    const cnt = counts.get(src) || 0;
    if (src && cnt >= perSourceCap) continue;
    counts.set(src, cnt + 1);
    selected.push(s);
  }
  return selected;
}

function tokenizeTitle(t: string): Set<string> {
  const stop = new Set(["THE","A","AN","OF","IN","ON","AND","OR","TO","FOR","WITH","AT","BY","FROM","ABOUT","OVER","AFTER","BEFORE","IS","ARE","WAS","WERE","AS","NEW","US"]);
  return new Set(
    t
      .toUpperCase()
      .replace(/[^A-Z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length >= 3 && !stop.has(w))
  );
}

function jaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 && b.size === 0) return 0;
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  const union = a.size + b.size - inter;
  return union === 0 ? 0 : inter / union;
}
