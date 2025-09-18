Summarize_v1 (provenance-first)

Inputs:
- Selected headlines (title, 1-sentence summary if available) with sources (URLs)
- Watchlist tickers (e.g., ["SPY","QQQ","IWM","GLD","BTC","UUP"])

Rules:
- No claims without a cited source. Tie every assertion to a URL.
- Limit 5 bullets for “What changed today”.
- Optionally add up to 3 bullets for “Looking ahead” if relevant.
- Style: crisp, factual, no hype. Include tickers in parentheses.

Output structure:
1) What changed today (≤5 bullets)
2) Looking ahead (≤3 bullets, optional)
3) Sources (list of links used)

